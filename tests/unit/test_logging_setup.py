"""Req 1 session log and req 35 daily log files."""

import datetime as dt
import logging

import pytest

from sirat_ui.app.logging_setup import DailyFileHandler


def make_logger(handler):
    logger = logging.getLogger(f"test.{id(handler)}")
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


@pytest.mark.req("35.persist")
def test_daily_log_uses_the_req_35_name_and_format(tmp_path):
    handler = DailyFileHandler(tmp_path, today=lambda: dt.date(2026, 10, 27))
    make_logger(handler).warning("Field value out of range")
    handler.close()
    line = (tmp_path / "sirat_2026-10-27.log").read_text(encoding="utf-8").strip()
    assert line.endswith("] [WARNING] Field value out of range")
    stamp = line[1:line.index("]")]
    dt.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S.%f")
    assert len(stamp.split(".")[1]) == 3  # milliseconds


def test_daily_log_switches_files_at_midnight(tmp_path):
    day = [dt.date(2026, 10, 27)]
    handler = DailyFileHandler(tmp_path, today=lambda: day[0])
    logger = make_logger(handler)
    logger.info("before")
    day[0] = dt.date(2026, 10, 28)
    logger.info("after")
    handler.close()
    assert "before" in (tmp_path / "sirat_2026-10-27.log").read_text(encoding="utf-8")
    assert "after" in (tmp_path / "sirat_2026-10-28.log").read_text(encoding="utf-8")


def test_logs_older_than_30_days_are_deleted(tmp_path):
    for name in ("sirat_2026-09-01.log", "sirat_2026-09-30.log", "sirat_2026-10-26.log", "notes.log"):
        (tmp_path / name).write_text("x")
    DailyFileHandler(tmp_path, today=lambda: dt.date(2026, 10, 27)).close()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["notes.log", "sirat_2026-09-30.log", "sirat_2026-10-26.log"]
