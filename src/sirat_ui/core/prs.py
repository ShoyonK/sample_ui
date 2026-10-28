"""PRS signal routing (req 24): pins, channels, the port/channel rule, fallback signals, and the register
operations a removed route is recorded as in History."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

PINS = [f"P{port}{n}" for port in "ABCD" for n in range(8)]
CHANNELS = list(range(12))
DISABLE = "DISABLE"

# Req 24 "Fallback Signals", used when the station can't list the chip family's signals.
FALLBACK_SIGNALS: Dict[str, List[str]] = {
    "MODEM": ["TIMDET", "PREDET", "FRAMEDET", "EOF", "ANT0", "ANT1"],
    "AGC": ["GAINADJUST", "GAINREDUCED"],
    "RAC": ["ACTIVE", "RX", "TX"],
    "SYNTH": ["INLOCK", "LOCK_WINDOW"],
    "CMU": ["HFXO", "HCLK"],
}

CONSTRAINT_TEXT = "Ports A/B can only use PRS channels 0-5. Ports C/D can only use PRS channels 6-11."


@dataclass(frozen=True)
class Signal:
    name: str
    category: str = ""

    @property
    def label(self) -> str:
        return f"{self.name}  ({self.category})" if self.category else self.name


def fallback_signals() -> List[Signal]:
    return [Signal(DISABLE)] + [Signal(name, cat) for cat, names in FALLBACK_SIGNALS.items() for name in names]


def split_pin(pin: str) -> Tuple[str, int]:
    """"PC3" -> ("C", 3)."""
    if len(pin) < 3 or pin[0] != "P" or pin[1] not in "ABCD" or not pin[2:].isdigit():
        raise ValueError(f"{pin} isn't a pin like PA0")
    return pin[1], int(pin[2:])


def channel_problem(pin: str, channel: int) -> Optional[str]:
    """Req 24 validation: None when the pin's port may use this channel."""
    port, _ = split_pin(pin)
    allowed = range(0, 6) if port in "AB" else range(6, 12)
    return None if channel in allowed else CONSTRAINT_TEXT


def allowed_channels(pin: str) -> List[int]:
    port, _ = split_pin(pin)
    return list(range(0, 6)) if port in "AB" else list(range(6, 12))


def removal_ops(pin: str, channel: int) -> List[Tuple[str, str, int]]:
    """Req 24 "Removing Route" step 3: (register, field, value) written when a route is disabled."""
    port, index = split_pin(pin)
    half = "H" if index >= 8 else "L"
    return [
        (f"PRS.ASYNC_CH{channel}_CTRL", "SOURCESEL", 0),
        (f"PRS.ASYNC_CH{channel}_CTRL", "SIGSEL", 0),
        ("GPIO.PRS0_ROUTEEN", f"ASYNCH{channel}PEN", 0),
        (f"GPIO.PRS0_ASYNCH{channel}ROUTE", "PORT", 0),
        (f"GPIO.PRS0_ASYNCH{channel}ROUTE", "PIN", 0),
        (f"GPIO.PORT{port}_MODE{half}", f"MODE{index}", 0),
    ]
