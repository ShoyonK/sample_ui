"""The crash guard: an unexpected error is logged and shown instead of closing SiBench (docs/CHAOS_TESTING.md)."""

import sys

from sibench_ui.app.crash_guard import make_hook
from sibench_ui.domains.logs.service import LogService
from sibench_ui.shared.interactions import ScriptedInteractions


def raised(exc):
    try:
        raise exc
    except BaseException:
        return sys.exc_info()


def test_an_unexpected_error_is_logged_and_shown_and_nothing_raises():
    log, ix = LogService(), ScriptedInteractions()
    make_hook(log, ix)(*raised(KeyError("lpmode_on")))
    assert log.lines[-1].level == "error" and log.lines[-1].text == "Unexpected error: KeyError: 'lpmode_on'"
    level, text = ix.toasts[-1]
    assert level == "error" and "KeyError" in text and "still running" in text


def test_a_failure_while_reporting_falls_back_to_printing(capsys):
    class Broken(ScriptedInteractions):
        def toast(self, level, text):
            raise RuntimeError("no window")

    make_hook(LogService(), Broken())(*raised(ValueError("boom")))      # must not raise
    assert "ValueError: boom" in capsys.readouterr().err


def test_ctrl_c_is_left_alone(capsys):
    ix = ScriptedInteractions()
    make_hook(LogService(), ix)(*raised(KeyboardInterrupt()))
    assert ix.toasts == [] and "KeyboardInterrupt" in capsys.readouterr().err
