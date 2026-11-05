"""Shared fixtures. Everything runs against the fake backend with a ManualScheduler (no sleeps)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

import pytest  # noqa: E402

from sirat_ui.gateway.fake import FakeStationGateway  # noqa: E402
from sirat_ui.gateway.scheduler import ManualScheduler  # noqa: E402
from support import Harness  # noqa: E402


@pytest.fixture
def harness(qapp, tmp_path) -> Harness:
    return Harness(tmp_path)


@pytest.fixture
def disconnected(qapp, tmp_path) -> Harness:
    return Harness(tmp_path, connect=False)


@pytest.fixture
def fake() -> FakeStationGateway:
    fake = FakeStationGateway(ManualScheduler())
    fake.connect_dut(1)
    return fake


def pytest_addoption(parser):
    group = parser.getgroup("chaos", "the seeded chaos runner (docs/CHAOS_TESTING.md)")
    group.addoption("--chaos-seed", type=int, default=None, help="replay one seed")
    group.addoption("--chaos-seeds", type=int, default=25, help="how many seeds to run, from 0")
    group.addoption("--chaos-steps", type=int, default=150, help="steps per seed")


def pytest_generate_tests(metafunc):
    if "chaos_seed" in metafunc.fixturenames:
        one = metafunc.config.getoption("--chaos-seed")
        seeds = [one] if one is not None else list(range(metafunc.config.getoption("--chaos-seeds")))
        metafunc.parametrize("chaos_seed", seeds)

