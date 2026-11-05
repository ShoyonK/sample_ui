"""Pop-out windows: pages, the watch list, the data logger and single graphs."""

from sirat_ui.domains.shell.windows import WindowsViewModel


def test_open_close_and_keys(qapp):
    vm = WindowsViewModel()
    vm.open("page", "watch")
    vm.open("watchList", "")
    vm.open("graph", "SYNTH.FREQ.FREQ")
    assert vm.openKeys == ["page:watch", "watchList", "graph:SYNTH.FREQ.FREQ"]
    assert [r["title"] for r in vm.model.items] == ["Watch and logger", "Watch list", "Graph · SYNTH.FREQ.FREQ"]
    assert vm.isOpen("graph", "SYNTH.FREQ.FREQ") and not vm.isOpen("logger", "")
    vm.close("watchList")
    assert vm.openKeys == ["page:watch", "graph:SYNTH.FREQ.FREQ"]


def test_opening_an_open_window_brings_it_to_the_front_instead(qapp):
    vm = WindowsViewModel()
    raised = []
    vm.raiseRequested.connect(raised.append)
    vm.open("logger", "")
    vm.open("logger", "")
    vm.show("logger")
    vm.show("watchList")  # not open: nothing to raise
    assert vm.openKeys == ["logger"] and raised == ["logger", "logger"]


def test_unknown_pages_and_empty_graphs_are_ignored(qapp):
    vm = WindowsViewModel()
    vm.open("page", "nope")
    vm.open("graph", "")
    vm.open("teleport", "")
    assert vm.openKeys == []


def test_every_nav_page_can_pop_out(harness):
    windows = harness.shell.windows
    for page in harness.shell.pages:
        windows.open("page", page["key"])
    assert len(windows.openKeys) == len(harness.shell.pages)
    windows.closeAll()
    assert windows.openKeys == []


def test_a_tool_opens_in_its_own_window_at_its_size(qapp):
    vm = WindowsViewModel()
    vm.open("tool", "dutControl")
    vm.open("tool", "nope")
    assert vm.openKeys == ["tool:dutControl"]
    row = vm.model.items[0]
    assert (row["title"], row["width"], row["height"]) == ("DUT control API explorer", 1200, 800)


def test_each_page_lists_the_parts_that_open_in_their_own_window():
    from sirat_ui.domains.shell.pages import PAGES
    parts = {p["key"]: [part["title"] for part in p["parts"]] for p in PAGES}
    assert parts["watch"] == ["Watch list", "Data logger"]
    assert parts["advanced"] == ["Python console", "Custom functions", "DUT control API explorer", "Memory viewer"]
    assert parts["instruments"] == ["Signal generator", "BLE packet", "GFSK packet", "RF switch",
                                    "Temperature chamber", "ECA capture"]
    assert parts["radio"] == ["PRS signal routing", "WiFi PHY configuration"]
    assert parts["settings"] == ["Hardware configuration", "System information"]
    watch = {part["title"]: part["key"] for p in PAGES if p["key"] == "watch" for part in p["parts"]}
    assert watch == {"Watch list": "watchList", "Data logger": "logger"}   # the window kinds they already had
