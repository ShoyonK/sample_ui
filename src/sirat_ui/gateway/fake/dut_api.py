"""A small stand-in for the DUT's Python API: `dut.dut_control`, `dut.rpc_io`, `dut.rm` and `dut.rta`.

The console and custom functions get it as `dut`; advanced.dut_control.describe introspects the same classes,
so the explorer, the console and recorded actions all see one API. A few calls fail the way real ones do
(RPC timeout, RAIL assert) so the explorer's error hints can be tried.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple

from sirat_ui.gateway.fake.memory import FakeMemory
from sirat_ui.gateway.fake.register_memory import RegisterMemory
from sirat_ui.models.registers import ChipInfo
from sirat_ui.models.station import ApiMethod, ApiModule, ApiPackage, ApiParam, ApiTree


class RpcTimeout(Exception):
    pass


class RpcTransportError(Exception):
    pass


class RailAssert(Exception):
    pass


for _error in (RpcTimeout, RpcTransportError, RailAssert):
    _error.__module__ = "rail"     # tracebacks show rail.RailAssert, not this fake's module path


class DutHost(Protocol):
    """What the fake DUT needs from the fake station."""
    ram: FakeMemory

    @property
    def rpc_timeout_s(self) -> float: ...

    @rpc_timeout_s.setter
    def rpc_timeout_s(self, seconds: float) -> None: ...   # dut.rta.lpw.SetRpcTimeout changes it

    @property
    def memory(self) -> RegisterMemory: ...

    @property
    def chip(self) -> ChipInfo: ...


class _Module:
    def __init__(self, dut: "FakeDut") -> None:
        self._dut = dut


# ---- common ---------------------------------------------------------------------------------------------

class CommonBle(_Module):
    """BLE helpers shared by every chip family."""

    def StartAdvertising(self, power: int = 0, channel: int = 37) -> bool:  # noqa: N802 (the DUT API's names)
        """Start legacy advertising on one primary channel.

        power is in dBm; channel is 37, 38 or 39."""
        if channel not in (37, 38, 39):
            raise RailAssert(f"RAIL assert 0x21: advertising channel {channel} isn't 37, 38 or 39")
        self._dut.state.update(advertising=True, adv_channel=channel, adv_power=power)
        return True

    def StopAdvertising(self) -> None:  # noqa: N802
        """Stop advertising."""
        self._dut.state["advertising"] = False

    def GetAdvertisingState(self) -> Dict[str, Any]:  # noqa: N802
        """Whether advertising is on, and on which channel and power."""
        s = self._dut.state
        return {"advertising": s.get("advertising", False), "channel": s.get("adv_channel"),
                "power_dbm": s.get("adv_power")}


class CommonSystem(_Module):
    """Firmware version, uptime and resets."""

    def GetVersion(self) -> str:  # noqa: N802
        """The RAIL test application's version string."""
        return "rail_test 2026.10.1"

    def GetUptime(self) -> float:  # noqa: N802
        """Seconds since the last reset."""
        return round(time.monotonic() - self._dut.reset_at, 3)

    def Delay(self, ms: int) -> None:  # noqa: N802
        """Block on the DUT for ms milliseconds. Longer than the RPC timeout fails."""
        if ms / 1000 > self._dut.host.rpc_timeout_s:
            raise RpcTimeout(f"RPC timeout after {self._dut.host.rpc_timeout_s:g} s waiting for Delay({ms})")

    def Reset(self, hard: bool = False) -> None:  # noqa: N802
        """Reset the radio state (hard=True also resets the uptime)."""
        self._dut.state.clear()
        if hard:
            self._dut.reset_at = time.monotonic()


# ---- host -----------------------------------------------------------------------------------------------

class HostGpio(_Module):
    """GPIO on the host board."""

    def SetPin(self, dut: Any, port: str, pin: int, value: bool) -> None:  # noqa: N802
        """Drive a GPIO pin high or low. port is A to D."""
        if port.upper() not in "ABCD" or not 0 <= pin <= 15:
            raise ValueError(f"No pin P{port}{pin}")
        self._dut.pins[f"P{port.upper()}{pin}"] = bool(value)

    def ReadPin(self, port: str, pin: int) -> bool:  # noqa: N802
        """Read a GPIO pin."""
        return self._dut.pins.get(f"P{port.upper()}{pin}", False)


class HostUart(_Module):
    """The host's debug UART."""

    def Send(self, text: str, baud: int = 115200) -> int:  # noqa: N802
        """Send text; returns the number of bytes sent."""
        return len(text.encode())


# ---- lpw ------------------------------------------------------------------------------------------------

class LpwRadio(_Module):
    """Low-power wireless radio control: channel, power, TX and RX."""

    def SetChannel(self, channel: int) -> None:  # noqa: N802
        """Select a channel of the loaded PHY (0 to 39)."""
        if not 0 <= channel <= 39:
            raise RailAssert(f"RAIL assert 0x0C: channel {channel} isn't in the PHY's channel config")
        self._dut.state["channel"] = channel

    def SetPower(self, power_dbm: float) -> float:  # noqa: N802
        """Set the TX power; returns the power the PA actually gives."""
        if not -30 <= power_dbm <= 20:
            raise RailAssert(f"RAIL assert 0x0F: TX power {power_dbm:g} dBm is out of range (-30 to 20 dBm)")
        actual = round(power_dbm * 2) / 2
        self._dut.state["power"] = actual
        return actual

    def GetRssi(self, samples: int = 1) -> int:  # noqa: N802
        """Average RSSI in dBm over a number of samples."""
        return -72 - (samples % 5)

    def StartTx(self, num_packets: int = 0, continuous: bool = False) -> None:  # noqa: N802
        """Start transmitting num_packets packets, or until StopTx when continuous."""
        self._dut.state.update(tx=True, tx_packets=num_packets, continuous=continuous)

    def StopTx(self) -> None:  # noqa: N802
        """Stop transmitting."""
        self._dut.state["tx"] = False

    def GetRxStats(self) -> Dict[str, int]:  # noqa: N802
        """Packet counters since the last reset."""
        return {"received": 1204, "crc_errors": 3, "sync_detects": 1260, "rx_overflows": 0}

    def ReadPacketLog(self, count: int = 20) -> List[int]:  # noqa: N802
        """RSSI of the last count received packets, newest last."""
        return [-70 - (i * 7) % 9 for i in range(count)]


class LpwBle(_Module):
    """BLE on the low-power wireless core."""

    def SetPhy(self, phy: str = "1M") -> str:  # noqa: N802
        """Switch the BLE PHY: 1M, 2M, Coded125k or Coded500k."""
        if phy not in ("1M", "2M", "Coded125k", "Coded500k"):
            raise ValueError(f"Unknown BLE PHY {phy!r}")
        self._dut.state["ble_phy"] = phy
        return phy

    def StartAdvertising(self, channel: int = 37, interval_ms: float = 100.0) -> bool:  # noqa: N802
        """Advertise on one channel at a fixed interval."""
        return CommonBle(self._dut).StartAdvertising(0, channel)


# ---- wifi -----------------------------------------------------------------------------------------------

class WifiWlan(_Module):
    """WiFi station control (Everest family only)."""

    def _need_wifi(self) -> None:
        if self._dut.host.chip.family.upper() != "EVEREST":
            raise RuntimeError(f"WiFi isn't available on {self._dut.host.chip.family.title()}")

    def GetMac(self) -> str:  # noqa: N802
        """The WiFi MAC address."""
        self._need_wifi()
        return "84:2E:14:00:12:34"

    def Scan(self, band: str = "2.4GHz") -> List[Dict[str, Any]]:  # noqa: N802
        """Scan for access points on a band."""
        self._need_wifi()
        return [{"ssid": "lab-ap", "channel": 6, "rssi": -48}, {"ssid": "bench-2", "channel": 11, "rssi": -63}]


PACKAGES: Tuple[Tuple[str, str, Tuple[Tuple[str, type], ...]], ...] = (
    ("Common", "common", (("ble", CommonBle), ("system", CommonSystem))),
    ("Host", "host", (("gpio", HostGpio), ("uart", HostUart))),
    ("LPW", "lpw", (("ble", LpwBle), ("radio", LpwRadio))),
    ("WiFi", "wifi", (("wlan", WifiWlan),)),
)


class _Package:
    def __init__(self, dut: "FakeDut", modules: Tuple[Tuple[str, type], ...]) -> None:
        for name, cls in modules:
            setattr(self, name, cls(dut))


class DutControl:
    def __init__(self, dut: "FakeDut") -> None:
        for _, attr, modules in PACKAGES:
            setattr(self, attr, _Package(dut, modules))


class RpcIo:
    def __init__(self, dut: "FakeDut") -> None:
        self._dut = dut

    def ReadByteBlock(self, address: int, size: int) -> bytes:  # noqa: N802
        start, data = self._dut.host.ram.read(address, size)
        return data[address - start:address - start + size]

    def Connect(self) -> None:  # noqa: N802
        pass


class RegisterMap:
    def __init__(self, dut: "FakeDut") -> None:
        self._dut = dut

    def readByName(self, name: str) -> int:  # noqa: N802
        return self._dut.host.memory.read(name)

    def writeByName(self, name: str, value: int) -> int:  # noqa: N802
        return self._dut.host.memory.write(name, value)


class _RtaLpw:
    def __init__(self, dut: "FakeDut") -> None:
        self._dut = dut

    def SetRpcTimeout(self, seconds: float) -> None:  # noqa: N802
        self._dut.host.rpc_timeout_s = float(seconds)

    def GetRSSI(self) -> int:  # noqa: N802
        return -72


class _Rta:
    def __init__(self, dut: "FakeDut") -> None:
        self.lpw = _RtaLpw(dut)


class FakeDut:
    def __init__(self, host: DutHost, position: int) -> None:
        self.host = host
        self.position = position
        self.state: Dict[str, Any] = {}
        self.pins: Dict[str, bool] = {}
        self.reset_at = time.monotonic()
        self.dut_control = DutControl(self)
        self.rpc_io = RpcIo(self)
        self.rm = RegisterMap(self)
        self.rta = _Rta(self)

    def __repr__(self) -> str:
        return f"<DUT {self.position}: {self.host.chip.part} {self.host.chip.revision}>"

    def method(self, path: str) -> Optional[Any]:
        """The bound method at "lpw.radio.SetPower", or None."""
        parts = path.split(".")
        if len(parts) != 3 or any(p.startswith("_") for p in parts):
            return None
        package = getattr(self.dut_control, parts[0], None)
        module = getattr(package, parts[1], None)
        method = getattr(module, parts[2], None)
        return method if callable(method) else None


# ---- describe ---------------------------------------------------------------------------------------------

def _annotation(param: inspect.Parameter) -> str:
    a = param.annotation
    return "" if a is inspect.Parameter.empty else inspect.formatannotation(a)


def _method(path: str, fn: Any) -> ApiMethod:
    sig = inspect.signature(fn, eval_str=True)
    params = tuple(
        ApiParam(p.name, _annotation(p), None if p.default is inspect.Parameter.empty else repr(p.default),
                 p.default is inspect.Parameter.empty)
        for p in sig.parameters.values() if p.name not in ("self", "dut"))   # dut is injected
    shown = sig.replace(parameters=[p for p in sig.parameters.values() if p.name not in ("self", "dut")])
    doc = (inspect.getdoc(fn) or "").split("\n\n")[0].replace("\n", " ")
    return ApiMethod(fn.__name__, path, f"{fn.__name__}{shown}", doc, params)


def describe() -> ApiTree:
    packages = []
    for title, attr, modules in PACKAGES:
        out = []
        for name, cls in modules:
            methods = tuple(_method(f"{attr}.{name}.{m}", getattr(cls, m)) for m in sorted(vars(cls))
                            if not m.startswith("_") and callable(getattr(cls, m)))
            out.append(ApiModule(name, f"{attr}.{name}", methods))
        packages.append(ApiPackage(title, tuple(out)))
    return ApiTree(tuple(packages))


def format_result(value: Any) -> str:
    """API doc "DUT control": lists show length and the first 10 items, dicts every pair, objects attributes."""
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        head = ", ".join(repr(v) for v in value[:10])
        more = f", … ({len(value) - 10} more)" if len(value) > 10 else ""
        return f"{type(value).__name__} of {len(value)}: [{head}{more}]"
    if isinstance(value, dict):
        return "\n".join(f"{k}: {v!r}" for k, v in value.items()) or "{}"
    attrs = {k: v for k, v in vars(value).items() if not k.startswith("_")} if hasattr(value, "__dict__") else {}
    return f"{type(value).__name__}\n" + "\n".join(f"  {k} = {v!r}" for k, v in attrs.items())
