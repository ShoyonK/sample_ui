# API change: WiFi PHY config, load_phy result, and PRS signal list

Status: proposed by the frontend. The fake backend implements it; the real Station API doesn't yet.

## Why

Two requirements need more than the current Station API design document gives:

1. **Req 23, WiFi PHY.** The WiFi PHY dialog builds a full configuration (mode, standard, channel, power
   mode, rate, TX parameters, advanced 802.11ax/be parameters) and calls `load_wifi_phy(test_obj, config)`.
   The API's `PhySpec` is `wifi(config_name)`, which can only name a stored configuration. The success
   dialog also shows the function called and the TestInputs overrides applied, which `LoadPhyRes: name`
   doesn't return.
2. **Req 24, PRS signals.** The original GUI imports the chip family's `pti_prs_module` and reads the signal
   names out of it. The frontend can't import station-side modules, and the API has no call that lists them.

## Proposed changes

### `dut.load_phy(pos, phy: PhySpec) -> LoadPhyRes`

```
PhySpec = lpw(name) | wifi(config: WifiPhyConfig)

WifiPhyConfig (req 23 "WiFi Config Structure"):
  mode: "RX" | "TX"
  standard: "802.11b" | "802.11g" | "802.11a" | "802.11n" | "802.11ac" | "802.11ax" | "802.11be"
  channel: int
  power_mode: "HP" | "LP" | "MP"
  rate: str                      # Mb/s for b/g/a, MCS index for n/ac/ax/be
  phy_name: str                  # e.g. WIFI_2p4G, PHY_WIFI_5G_HP
  tx_params?: { pkt_length: 1..65535, num_pkts: 0..1000000,
                transmit_mode: "BURST" | "CONTINUES" | "STREAM", aggr_enable: bool }
  advanced?:  { ppdu_type: str, gi_ltf: str, dcm: 0 | 1, bandwidth: "BW_20MHz" | ... }

LoadPhyRes:
  name: str
  function: str                  # "reset_and_download_lpw_phy" or "load_wifi_phy"
  overrides: [[key, value], ...] # TestInputs overrides applied (WiFi); empty for LPW
```

`wifi(...)` on a non-Everest DUT fails with `INVALID_PARAMS`.

### `rf.prs_signals(pos) -> PrsSignalCatalog` (new)

```
PrsSignalCatalog:
  family: str                    # dut.info.hw.CHIPREVHW_FAMILY_NAME
  module: str                    # the module the names came from
  signals: [str]                 # unique prsMap keys, sorted
requires: dut
```

If the call fails, the frontend falls back to the req 24 "Fallback Signals" list and says so.

### `rf.prs_route(pos, PrsRoute) -> Empty` (unchanged, typed)

`PrsRoute: { signal, pin: "PA0".."PD7", channel: 0..11 }`. `signal = "DISABLE"` removes a route. The
service should reject port A/B with channels 6-11 and port C/D with 0-5 (`INVALID_PARAMS`); the frontend
checks first and shows req 24's warning.

## Frontend side

- Typed models: `LpwPhy`, `WifiPhy`, `LoadPhyResult`, `PrsRoute`, `PrsSignalCatalog` in
  `src/sirat_ui/gateway/models.py`; `WifiPhyConfig` in `src/sirat_ui/core/wifi.py`.
- Port: `StationGateway.load_phy`, `prs_route`, `prs_signals` in `src/sirat_ui/gateway/port.py`.
