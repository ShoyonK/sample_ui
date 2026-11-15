"""The whole app over the real wire: `sibench --backend fake-tcp` (docs/JSONRPC_MIGRATION.md section 5)."""

from pages import RegistersPage
from sibench_ui.app.launch import build_app
from sibench_ui.gateway.api.client import ApiStationGateway


def test_the_app_connects_and_reads_a_register_over_tcp(qapp, qtbot, tmp_path):
    app, scenario = build_app("fake-tcp", "happy", home=tmp_path, seed_demo=False, dumps=tmp_path / "dumps")
    gateway = app.container.gateway
    assert isinstance(gateway, ApiStationGateway)
    try:
        app.load()
        app.window.resize(1600, 950)
        qtbot.waitExposed(app.window)
        app.container.start(autoconnect=scenario.autoconnect, position=1)
        qtbot.waitUntil(lambda: app.container.state.connected, timeout=5000)
        page = RegistersPage(app, qtbot)
        page.open_register("BUFC.LPMODE")
        page.click("readButton")
        page.wait_for(lambda: page.value_text().startswith("0x"))
        assert "over TCP" in app.container.state.backend_label
    finally:
        app.shutdown()
        gateway.close()
