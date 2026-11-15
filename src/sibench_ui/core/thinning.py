"""Thinning a series for a plot: a plot is about 1,000 pixels wide, so it never needs every point of a long run."""

from __future__ import annotations

from typing import List, Sequence, Tuple


def thin(xs: Sequence[float], ys: Sequence[float], buckets: int) -> Tuple[List[float], List[float]]:
    """At most 2 * buckets points, keeping each bucket's min and max so spikes survive. Short series pass through."""
    n = len(xs)
    if n <= buckets * 2:
        return list(xs), list(ys)
    out_x: List[float] = []
    out_y: List[float] = []
    step = n / buckets
    for b in range(buckets):
        start, end = int(b * step), int((b + 1) * step)
        chunk = range(start, end)
        low = min(chunk, key=ys.__getitem__)
        high = max(chunk, key=ys.__getitem__)
        for i in sorted({low, high}):
            out_x.append(xs[i])
            out_y.append(ys[i])
    # The newest point always shows, so the plot's right edge and the last value agree
    if out_x[-1] != xs[-1]:
        out_x.append(xs[-1])
        out_y.append(ys[-1])
    return out_x, out_y
