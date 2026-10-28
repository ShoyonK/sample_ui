"""Render the real QML app offscreen and save screenshots of key states.

    uv run python scripts/screenshot.py --out docs/screenshots
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Only a native platform can grab QML frames, so the window is parked off-screen instead.
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PyQt5.QtCore import QEventLoop, QTimer  # noqa: E402

from sirat_ui.app.launch import build_app  # noqa: E402


def pump(app, ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec_()


def find_item(item, name: str):
    """List delegates and other visual items have no QObject parent, so walk the visual tree."""
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


def grab(app, path: Path) -> None:
    image = app.window.grabWindow()
    ok = not image.isNull() and image.save(str(path), "PNG")
    print("saved" if ok else "FAILED", path, image.size())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    home = Path(tempfile.mkdtemp(prefix="sirat_shot_"))
    app, scenario = build_app("fake", "happy", home=home, seed_demo=True, dumps=home / "dumps")
    app.load()
    app.window.setPosition(-4000, -4000)
    app.container.start(autoconnect=True)
    shell, state, catalog = app.container.shell, app.container.state, app.container.services.catalog
    pump(app, 1500)

    # Registers: open BUFC.LPMODE, read it twice so a changed field shows
    state.select(catalog.register("BUFC.LPMODE"), by_user=True)
    pump(app, 300)
    shell.detail.write("0x3")
    pump(app, 400)
    grab(app, args.out / "01_registers.png")

    shell.navigate("watch")
    shell.watch.toggleLive()
    shell.logger.toggleRecording()
    pump(app, 4500)
    grab(app, args.out / "02_watch_logger.png")

    shell.navigate("sequences")
    shell.sequences.run()
    pump(app, 1200)
    grab(app, args.out / "03_sequences.png")
    pump(app, 2500)

    shell.navigate("registers")
    state.select(catalog.register("CMU.CLKEN0"), by_user=True)
    pump(app, 300)
    shell.detail.write("0xF0F")
    pump(app, 400)
    grab(app, args.out / "04_confirm_critical_write.png")
    shell.dialogs.answerConfirm(False, False)
    pump(app, 300)

    app.container.gateway.drop_dut(1, "RPC connection lost", "registers.read")
    pump(app, 400)
    grab(app, args.out / "05_disconnect_recovery.png")
    shell.recovery.reconnect()
    pump(app, 1500)
    shell.recovery.dismiss()
    pump(app, 300)

    shell.connection.openSheet()
    pump(app, 500)
    grab(app, args.out / "06_connect_sheet.png")
    shell.connection.closeSheet()

    shell.navigate("actions")
    names = [r["name"] for r in shell.actions.model.items]
    shell.actions.select(names.index("lpmode_on"))
    shell.actions.runCurrent()
    pump(app, 1500)
    shell.actions.select(names.index("siggen_2440_0dbm"))
    pump(app, 300)
    grab(app, args.out / "08_actions.png")
    shell.actions.viewCurrent()
    pump(app, 500)
    grab(app, args.out / "09_action_view.png")
    shell.actionEditor.closeView()
    shell.actions.select(names.index("ble_1m_rx_setup"))
    shell.actions.editCurrent()
    pump(app, 500)
    grab(app, args.out / "10_action_edit.png")
    shell.actionEditor.cancelEdit()
    pump(app, 300)

    shell.palette.open()
    shell.palette.setQuery("mode")
    pump(app, 400)
    grab(app, args.out / "11_command_palette.png")
    shell.palette.close()
    pump(app, 200)

    shell.navigate("settings")
    pump(app, 600)
    grab(app, args.out / "12_settings.png")

    services = app.container.services
    services.sessions.save("Bring-up day 1")
    services.sessions.save("BLE 1M RX sweep")
    shell.sessions.openBrowser()
    shell.sessions.select(0)
    pump(app, 500)
    grab(app, args.out / "13_session_browser.png")
    shell.sessions.closeBrowser()
    pump(app, 200)

    # Dumps: take two dumps with a change in between, then compare them
    shell.navigate("dumps")
    dumps = app.container.services.dumps
    for name in ("before_lpmode", "after_lpmode"):
        dumps.take(["BUFC", "MODEM", "SYNTH"], lambda job, n=name: dumps.save(dumps.new_dump(job, n)))
        pump(app, 2500)
        state.select(catalog.register("BUFC.LPMODE"), by_user=True)
        shell.detail.write("0x1")
        pump(app, 1200)
    shell.dumps.select(1)
    pump(app, 300)
    files = dumps.files()
    shell.dumps._compare(files[1].path, files[0].path)
    pump(app, 600)
    grab(app, args.out / "14_dumps.png")
    shell.dumps.openPicker()
    pump(app, 500)
    grab(app, args.out / "15_dump_picker.png")
    shell.dumps.closePicker()
    pump(app, 200)

    # Radio Calculator diff with the sample config, sorted by status
    from sirat_ui.core.radio_config import parse_config
    sample = Path(__file__).resolve().parent.parent / "docs" / "samples" / "PHY_demo.cfg"
    config = parse_config(sample.read_text(encoding="utf-8"), sample.name)
    dumps.radio_diff(config, list(config.field_counts), shell.dumps._show_radio)
    pump(app, 1500)
    shell.dumps.sortBy("status")
    pump(app, 400)
    grab(app, args.out / "16_radio_diff.png")
    help_tip = find_item(app.window.contentItem(), "comparisonHelp")
    if help_tip is not None:
        help_tip.setProperty("pinned", True)
        pump(app, 400)
        grab(app, args.out / "17_radio_help.png")
        help_tip.setProperty("pinned", False)

    shell.state.toggleDarkMode()
    state.select(catalog.register("BUFC.LPMODE"), by_user=True)
    pump(app, 600)
    grab(app, args.out / "07_registers_dark.png")
    app.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
