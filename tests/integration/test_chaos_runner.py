"""The seeded chaos runner (docs/CHAOS_TESTING.md, phase 3).

The full run is marked `chaos` and left out of the normal test run:
    uv run pytest -m chaos                       # 25 seeds x 150 steps
    uv run pytest -m chaos --chaos-seed 7        # replay one seed
    uv run pytest -m chaos --chaos-seeds 300     # the nightly run
A short smoke run stays in the normal suite so the runner itself doesn't rot.
"""

import pytest

from chaos_runner import play


def test_chaos_smoke(qapp, tmp_path):
    play(seed=0, steps=60, home=tmp_path)


@pytest.mark.chaos
def test_chaos(qapp, tmp_path, request, chaos_seed):
    play(seed=chaos_seed, steps=request.config.getoption("--chaos-steps"), home=tmp_path)
