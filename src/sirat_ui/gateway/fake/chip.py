"""A small fake chip chosen to exercise every UI rule.

- CMU, EMU: critical (writes need confirmation)
- USART0: read-sensitive (refused by watch and read_many)
- BUFC.BUF0_CTRL: has read-only bits, so some writes fail verification
- BUFC.IPVERSION: read-only, BUFC.BUF0_CMD: write-only
- _NS/_S variants: hidden unless "Show peripherals with _NS/_S" is on
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from sirat_ui.models.registers import AccessType, EnumValue, FieldDef, PeripheralDef, RegisterDef

RO, WO, RW = AccessType.READ_ONLY, AccessType.WRITE_ONLY, AccessType.READ_WRITE

CHIP_PART, CHIP_REVISION, CHIP_FAMILY = "EFR32XG29XFULL", "A0", "LION"

_FieldSpec = Tuple  # (name, lsb, width, access, description, enums)


def _e(*pairs: Tuple[str, int]) -> Tuple[EnumValue, ...]:
    return tuple(EnumValue(name, value) for name, value in pairs)


def _reg(periph: str, base: int, name: str, offset: int, access: AccessType, desc: str,
         fields: Sequence[_FieldSpec] = (), reset: int = 0, critical: bool = False,
         read_sensitive: bool = False) -> RegisterDef:
    full = f"{periph}.{name}"
    field_defs = tuple(
        FieldDef(full, f[0], f[1], f[2], f[3] if len(f) > 3 else access, f[4] if len(f) > 4 else "",
                 f[5] if len(f) > 5 else ())
        for f in fields
    )
    return RegisterDef(periph, name, base + offset, access, 32, desc, field_defs, reset, critical, read_sensitive)


def _periph(name: str, base: int, desc: str, regs: Sequence[tuple], critical: bool = False,
            read_sensitive: bool = False) -> PeripheralDef:
    registers = tuple(_reg(name, base, *r, critical=critical, read_sensitive=read_sensitive) for r in regs)
    return PeripheralDef(name, base, desc, registers)


_BUFC = [
    ("IPVERSION", 0x00, RO, "IP version", [("IPVERSION", 0, 32, RO, "IP version")], 0x3),
    ("EN", 0x04, RW, "Module enable", [("EN", 0, 1, RW, "Enable", _e(("DISABLED", 0), ("ENABLED", 1)))], 0x1),
    ("LPMODE", 0x08, RW, "Low power mode", [
        ("LPENBYM33", 1, 1, RW, "Low power mode enable from M33", _e(("DISABLED", 0), ("ENABLED", 1))),
        ("LPENBYSEQ", 0, 1, RW, "Low power mode enable from M0p sequencer", _e(("DISABLED", 0), ("ENABLED", 1))),
    ], 0x1),
    ("BUF0_CTRL", 0x0C, RW, "Buffer 0 control", [
        ("SIZE", 0, 3, RW, "Buffer size", _e(("SIZE64", 0), ("SIZE128", 1), ("SIZE256", 2), ("SIZE512", 3))),
        ("RESERVED", 3, 5, RO, "Reserved, reads as zero"),
    ]),
    ("BUF0_ADDR", 0x10, RW, "Buffer 0 address", [("ADDR", 2, 30, RW, "Word-aligned address")]),
    ("BUF0_WRITEOFFSET", 0x14, RW, "Buffer 0 write offset", [("WRITEOFFSET", 0, 13, RW, "Write offset")]),
    ("BUF0_READOFFSET", 0x18, RO, "Buffer 0 read offset", [("READOFFSET", 0, 13, RO, "Read offset")]),
    ("BUF0_CMD", 0x1C, WO, "Buffer 0 command", [("CLEAR", 0, 1, WO, "Clear buffer"), ("PREFETCH", 1, 1, WO, "Prefetch")]),
    ("BUF0_STATUS", 0x20, RO, "Buffer 0 status", [("BYTES", 0, 13, RO, "Bytes in buffer")]),
    ("BUF0_THRESHOLDCTRL", 0x24, RW, "Buffer 0 threshold control", [("THRESHOLD", 0, 13, RW, "Threshold")]),
]

_AGC = [
    ("IPVERSION", 0x00, RO, "IP version", [("IPVERSION", 0, 32, RO, "IP version")], 0x2),
    ("EN", 0x04, RW, "Module enable", [("EN", 0, 1, RW, "Enable", _e(("DISABLED", 0), ("ENABLED", 1)))], 0x1),
    ("RSSI", 0x08, RO, "Received signal strength", [("RSSI", 0, 16, RO, "RSSI in dBm, two's complement")], 0xFFB4),
    ("CTRL0", 0x0C, RW, "Control 0", [("PWRTARGET", 0, 8, RW, "Power target"), ("MODE", 8, 2, RW, "Gain mode",
                                                                             _e(("CONT", 0), ("LOCKPREDET", 1), ("LOCKFRAMEDET", 2)))]),
]

_CMU = [
    ("CTRL", 0x00, RW, "Control", [("CLKOUTSEL0", 0, 5, RW, "Clock output select 0")]),
    ("CLKEN0", 0x64, RW, "Clock enable 0", [
        ("LDMA", 0, 1, RW, "LDMA clock enable"), ("LDMAXBAR", 1, 1, RW, "LDMAXBAR clock enable"),
        ("RADIOAES", 2, 1, RW, "RADIOAES clock enable"), ("GPCRC", 3, 1, RW, "GPCRC clock enable"),
        ("TIMER0", 8, 1, RW, "TIMER0 clock enable"), ("TIMER1", 9, 1, RW, "TIMER1 clock enable"),
        ("TIMER2", 10, 1, RW, "TIMER2 clock enable"), ("TIMER3", 11, 1, RW, "TIMER3 clock enable"),
    ], 0xF07),
    ("SYSCLKCTRL", 0x70, RW, "System clock control", [
        ("CLKSEL", 0, 3, RW, "Clock select", _e(("FSRCO", 1), ("HFRCODPLL", 2), ("HFXO", 3), ("CLKIN0", 4)))], 0x3),
]

_EMU = [
    ("CTRL", 0x00, RW, "Control", [("EM2DBGEN", 0, 1, RW, "Enable debugging in EM2")]),
    ("STATUS", 0x04, RO, "Status", [("LOCK", 0, 1, RO, "Lock status")]),
]

_GPIO = [
    ("PA_MODEL", 0x04, RW, "Port A mode low", [
        ("MODE0", 0, 4, RW, "Pin 0 mode", _e(("DISABLED", 0), ("INPUT", 1), ("INPUTPULL", 2), ("PUSHPULL", 4))),
        ("MODE1", 4, 4, RW, "Pin 1 mode", _e(("DISABLED", 0), ("INPUT", 1), ("INPUTPULL", 2), ("PUSHPULL", 4))),
    ]),
    ("PA_DOUT", 0x0C, RW, "Port A data out", [("DOUT", 0, 16, RW, "Data out")]),
    ("LOCK", 0x300, WO, "Configuration lock", [("LOCKKEY", 0, 16, WO, "Lock key")]),
]

_MODEM = [
    ("CTRL", 0x00, RW, "Modem control", [
        ("OPMODE", 0, 2, RW, "Operating mode", _e(("IDLE", 0), ("TX", 1), ("RX", 2))),
        ("CODING", 2, 4, RW, "Coding scheme"),
        ("DEMODSEL", 8, 3, RW, "Demodulator select"),
    ], 0x2),
    ("STATUS", 0x04, RO, "Modem status", [("DEMODSTATE", 0, 3, RO, "Demodulator state")]),
]

_RAC = [
    ("STATUS", 0x00, RO, "Radio controller status", [
        ("STATE", 0, 4, RO, "Radio state", _e(("OFF", 0), ("RXWARM", 1), ("RXSEARCH", 3), ("RXFRAME", 4),
                                               ("TXWARM", 6), ("TX", 7))),
    ], 0x3),
    ("CTRL", 0x04, RW, "Radio controller control", [("FORCEDISABLE", 0, 1, RW, "Force radio off")]),
]

_SYNTH = [
    ("FREQ", 0x10, RW, "Synthesizer frequency", [("FREQ", 0, 28, RW, "Frequency word")], 2_440_000),
    ("CHCTRL", 0x14, RW, "Channel control", [("CHNO", 0, 6, RW, "Channel number")]),
]

_FRC = [
    ("STATUS", 0x00, RO, "Frame controller status", [("ACTIVE", 0, 1, RO, "Frame controller active")], 0x1),
    ("CTRL", 0x04, RW, "Frame controller control", [("RANDOMTX", 0, 1, RW, "Random TX data")]),
]

_USART = [
    ("CTRL", 0x00, RW, "Control", [("SYNC", 0, 1, RW, "Synchronous mode")]),
    ("STATUS", 0x04, RO, "Status", [("RXDATAV", 7, 1, RO, "RX data valid")]),
    ("RXDATA", 0x1C, RO, "RX data (reading pops the FIFO)", [("RXDATA", 0, 8, RO, "RX data")]),
]

_SIMPLE = [
    ("CTRL", 0x00, RW, "Control", [("EN", 0, 1, RW, "Enable"), ("INV", 1, 1, RW, "Invert output")]),
    ("STATUS", 0x04, RO, "Status", [("OUT", 0, 1, RO, "Output")]),
]


def build_chip() -> List[PeripheralDef]:
    peripherals = [
        _periph("ACMP0", 0x5A008000, "Analog comparator", _SIMPLE),
        _periph("AGC", 0xB800C000, "Automatic gain control", _AGC),
        _periph("AMUXCP0", 0x5A020000, "Analog mux charge pump", _SIMPLE),
        _periph("BUFC", 0xBA000000, "Buffer controller", _BUFC),
        _periph("CMU", 0x40008000, "Clock management unit", _CMU, critical=True),
        _periph("EMU", 0x40004000, "Energy management unit", _EMU, critical=True),
        _periph("FRC", 0xA8004000, "Frame controller", _FRC),
        _periph("GPIO", 0x5003C000, "General purpose I/O", _GPIO),
        _periph("MODEM", 0xB8014000, "Modem", _MODEM),
        _periph("RAC", 0xA8020000, "Radio controller", _RAC),
        _periph("SYNTH", 0xA8018000, "Synthesizer", _SYNTH),
        _periph("USART0", 0x5005C000, "Universal synchronous/asynchronous receiver/transmitter", _USART,
                read_sensitive=True),
    ]
    variants = []
    for name, base, desc, regs, critical in (("AGC", 0xB800C000, "Automatic gain control", _AGC, False),
                                             ("BUFC", 0xBA000000, "Buffer controller", _BUFC, False),
                                             ("CMU", 0x40008000, "Clock management unit", _CMU, True)):
        variants.append(_periph(f"{name}_NS", base, f"{desc} (non-secure)", regs, critical=critical))
        variants.append(_periph(f"{name}_S", base - 0x10000000, f"{desc} (secure)", regs, critical=critical))
    return peripherals + variants
