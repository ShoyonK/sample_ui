"""EcaService (req 30): trigger and channel sources, start a capture, fetch it page by page, save it as CSV.

A capture is an instrument activity; when it finishes, its result names the capture, which instruments.eca.result
returns in pages until `more` is false (the station drops it after the last page).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from sirat_ui.core.eca import decode, to_csv
from sirat_ui.core.observable import Event
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.port import InstrumentsPort
from sirat_ui.models.instruments import Capture
from sirat_ui.models.station import ActivityFinished, ActivityProgress, CapturePage, CaptureSpec, EcaSources
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState

KIND = "eca"
PAGE = 65536


class EcaService:
    def __init__(self, gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, errors: ErrorPresenter,
                 log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._bench = bench
        self._errors = errors
        self._log = log
        self.sources: Optional[EcaSources] = None
        self.capture: Optional[Capture] = None
        self.activity = ""
        self.progress_text = ""
        self.downloading = False
        self.changed = Event()
        self._was_connected = False
        state.changed.connect(self._on_state)
        self._on_state()

    @property
    def instrument_id(self) -> str:
        return self._bench.instrument_id(KIND)

    def can(self, method: str) -> bool:
        return bool(self.instrument_id) and self._state.can(method, self.instrument_id)

    @property
    def busy(self) -> bool:
        return bool(self.activity) or self.downloading

    def _on_state(self, *_: object) -> None:
        found = self._bench.instrument(KIND)
        connected = bool(found and found.connected)
        if connected and not self._was_connected:
            self.load_sources()
        self._was_connected = connected
        self.changed.emit()

    def load_sources(self) -> Call[EcaSources]:
        def loaded(sources: EcaSources) -> None:
            self.sources = sources
            self.changed.emit()

        return self._gateway.eca_sources(self.instrument_id).then(
            loaded, lambda e: self._log.warning(f"Couldn't load the ECA sources ({e.message})"))

    def start(self, spec: CaptureSpec) -> Call[str]:
        def started(activity_id: str) -> None:
            self.activity = activity_id
            self.progress_text = "Starting"
            self._bench.follow(activity_id, self._progress, self._finished)
            self.changed.emit()

        return self._gateway.eca_capture(self.instrument_id, spec).then(
            started, lambda e: self._errors.present(e, "Start capture"))

    def abort(self) -> None:
        if self.activity:
            self._bench.abort(self.activity)

    def _progress(self, event: ActivityProgress) -> None:
        self.progress_text = f"{event.message} ({event.step}/{event.total})"
        self.changed.emit()

    def _finished(self, event: ActivityFinished) -> None:
        self.activity = ""
        capture_id = (event.result or {}).get("capture_id") if event.ok else None
        if capture_id:
            self._download(str(capture_id))
        else:
            self.progress_text = "Stopped" if event.error is None else event.error.message
            if event.error is not None:
                self._errors.present(event.error, "ECA capture")
        self.changed.emit()

    def _download(self, capture_id: str) -> None:
        """Pages until `more` is false, then the whole capture replaces the previous one."""
        self.downloading = True
        self.progress_text = "Downloading"
        channels: Dict[str, List[int]] = {}

        def page_arrived(page: CapturePage) -> None:
            for name, data in page.channels.items():
                channels.setdefault(name, []).extend(decode(data))
            if page.more:
                self.progress_text = f"Downloading ({page.offset + page.count:,} of {page.meta.sample_count:,})"
                self.changed.emit()
                fetch(page.offset + page.count)
                return
            self.downloading = False
            self.capture = Capture(page.meta, channels)
            self.progress_text = f"{page.meta.sample_count:,} samples on {len(channels)} channels"
            self._log.success(f"ECA capture downloaded ({self.progress_text})")
            self.changed.emit()

        def failed(error: ApiError) -> None:
            self.downloading = False
            self.progress_text = error.message
            self._errors.present(error, "Download capture")
            self.changed.emit()

        def fetch(offset: int) -> None:
            self._gateway.eca_result(capture_id, offset, PAGE).then(page_arrived, failed)

        fetch(0)

    def save_csv(self, path: Path) -> None:
        if self.capture is None:
            return
        Path(path).write_text(to_csv(self.capture), encoding="utf-8")
        self._log.success(f"Saved the ECA capture to {path}")
