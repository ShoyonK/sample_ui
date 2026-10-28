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
