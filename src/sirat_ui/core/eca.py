"""ECA captures (req 30): decode pages, plot-ready decimation, timing measurements and CSV export.

Pure functions over plain lists, so the ViewModel stays thin and the tests can check the numbers.
"""

from __future__ import annotations

import base64
import datetime as dt
import sys
from array import array
from typing import List, Optional, Sequence, Tuple

from sirat_ui.models.instruments import Capture, Measurement

PLOT_POINTS = 1200   # min/max pairs per channel are plenty for a plot a few hundred pixels wide
MAX_SAMPLES = 1_000_000   # per channel, the most one capture holds (instruments.eca.capture)


def decode(page_channel: str) -> List[int]:
    """One channel of a CapturePage: base64 little-endian int16 -> sample values (mV)."""
    samples = array("h")
    samples.frombytes(base64.b64decode(page_channel))
    if sys.byteorder == "big":   # the wire is little-endian
        samples.byteswap()
    return samples.tolist()


def decimate(values: Sequence[int], rate_hz: float, points: int = PLOT_POINTS,
             window: Optional[Tuple[float, float]] = None) -> Tuple[List[float], List[float]]:
    """Thins one channel for plotting, keeping each bucket's min and max so short pulses stay visible.

    The same idea as core/thinning.thin, but over a sample range and with x converted to ms.

    Args:
        values: The channel's samples.
        rate_hz: The sample rate, to turn sample indexes into ms.
        points: How many buckets; the result has at most twice as many points.
        window: (from_ms, to_ms) to plot only that range, so zooming in shows full detail.

    Returns:
        (x in ms, y). Short ranges come back unthinned.
    """
    n = len(values)
    lo, hi = 0, n
    if window is not None:
        lo = max(0, int(window[0] * 1e-3 * rate_hz))
        hi = min(n, int(window[1] * 1e-3 * rate_hz) + 2)
    span = hi - lo
    if span <= 0:
        return [], []
    if span <= points * 2:
        return [i / rate_hz * 1e3 for i in range(lo, hi)], [float(values[i]) for i in range(lo, hi)]
    xs: List[float] = []
    ys: List[float] = []
    step = span / points
    for b in range(points):
        start, end = lo + int(b * step), lo + int((b + 1) * step)
        if start >= end:
            continue
        chunk = values[start:end]
        i_min = start + min(range(len(chunk)), key=chunk.__getitem__)
        i_max = start + max(range(len(chunk)), key=chunk.__getitem__)
        for i in sorted((i_min, i_max)):
            xs.append(i / rate_hz * 1e3)
            ys.append(float(values[i]))
    return xs, ys


def measure(channel: str, values: Sequence[int], rate_hz: float) -> Measurement:
    """Measures one channel: range, mean, rising edges, frequency, mean pulse width and the first rise.

    An edge crosses the midpoint between min and max, with 10 % hysteresis either side so noise doesn't count.

    Args:
        channel: The channel's name, copied into the result.
        values: The samples (mV).
        rate_hz: The sample rate.
    """
    if not values:
        return Measurement(channel, 0, 0, 0.0, 0, None, None, None)
    lo, hi = min(values), max(values)
    mean = sum(values) / len(values)
    rises: List[int] = []
    widths: List[int] = []
    if hi - lo > 0:
        upper, lower = lo + (hi - lo) * 0.6, lo + (hi - lo) * 0.4
        high = values[0] > upper
        rose_at: Optional[int] = None
        for i, v in enumerate(values):
            if not high and v > upper:
                high = True
                rises.append(i)
                rose_at = i
            elif high and v < lower:
                high = False
                if rose_at is not None:
                    widths.append(i - rose_at)
                rose_at = None
    frequency = None
    if len(rises) >= 2:
        period = (rises[-1] - rises[0]) / (len(rises) - 1) / rate_hz
        frequency = 1 / period if period > 0 else None
    high_time = sum(widths) / len(widths) / rate_hz * 1e6 if widths else None
    first = rises[0] / rate_hz * 1e3 if rises else None
    return Measurement(channel, lo, hi, mean, len(rises), frequency, high_time, first)


def format_frequency(hz: Optional[float]) -> str:
    if hz is None:
        return "—"
    for unit, scale in (("MHz", 1e6), ("kHz", 1e3)):
        if hz >= scale:
            return f"{hz / scale:.3g} {unit}"
    return f"{hz:.3g} Hz"


def format_ms(ms: float) -> str:
    """Times in the unit that reads best: 0.376 ms -> '376 µs'."""
    if abs(ms) < 1:
        return f"{ms * 1e3:.4g} µs"
    return f"{ms:.4g} ms"


def to_csv(capture: Capture) -> str:
    """Req 30 "Capture Storage": CSV with the configuration and timestamp in # comment lines."""
    spec = capture.meta.spec
    started = dt.datetime.fromtimestamp(capture.meta.started_at).strftime("%Y-%m-%d %H:%M:%S")
    names = list(capture.channels)
    lines = [
        "# SiRAT ECA capture",
        f"# started: {started}",
        f"# chip: {capture.meta.chip}",
        f"# channels: {', '.join(names)}",
        f"# trigger: {spec.trigger} ({spec.edge}), pretrigger {spec.pretrigger_pct} %",
        f"# sample_rate_hz: {spec.sample_rate_hz:g}",
        f"# duration_s: {spec.duration_s:g}",
        f"# samples: {capture.meta.sample_count}",
        "# values in mV",
        ",".join(["time_s"] + names),
    ]
    count = capture.meta.sample_count
    columns = [capture.channels[n] for n in names]
    for i in range(count):
        lines.append(",".join([f"{i / spec.sample_rate_hz:.9g}"] + [str(col[i]) for col in columns]))
    return "\n".join(lines) + "\n"
