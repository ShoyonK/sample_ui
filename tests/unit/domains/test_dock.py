"""The bottom dock: open or collapsed per page, and a strip that still shows what's happening."""

from support import Harness


def test_watch_and_sequences_start_collapsed_other_pages_open(harness):
    shell = harness.shell
    assert shell.currentPage == "registers" and not shell.dock.collapsed
    for page, collapsed in (("watch", True), ("sequences", True), ("dumps", False), ("actions", False)):
        shell.navigate(page)
        assert shell.dock.collapsed is collapsed, page


def test_each_page_remembers_whether_the_dock_is_open(harness):
    shell = harness.shell
    shell.dock.toggle()                      # hide it on Registers
    shell.navigate("watch")
    shell.dock.show()                        # open it on Watch
    shell.navigate("dumps")
    assert not shell.dock.collapsed          # untouched pages keep their default
    shell.navigate("registers")
    assert shell.dock.collapsed
    shell.navigate("watch")
    assert not shell.dock.collapsed


def test_the_strip_shows_the_last_write_checked_actions_and_newest_log_line(harness):
    dock = harness.shell.dock
    harness.select("BUFC.LPMODE")
    harness.shell.detail.write("0x3")
    assert dock.lastHistory == "Write  BUFC.LPMODE = 0x3"
    assert "BUFC.LPMODE" in dock.lastLog and dock.lastLogLevel in ("success", "info")
    enabled = sum(1 for a in harness.services.actions.actions.values() if a.enabled)
    assert dock.checkedCount == enabled
    first = next(iter(harness.services.actions.actions))
    harness.services.actions.set_enabled(first, not harness.services.actions.actions[first].enabled)
    assert dock.checkedCount != enabled


def test_strip_before_anything_happened(qapp, tmp_path):
    dock = Harness(tmp_path, seed=False, connect=False).shell.dock
    assert dock.lastHistory == "No reads or writes yet" and dock.checkedCount == 0
