from sirat_ui.core.thinning import thin


def test_short_series_pass_through():
    assert thin([0, 1, 2], [5.0, 6.0, 7.0], 10) == ([0, 1, 2], [5.0, 6.0, 7.0])


def test_a_long_series_keeps_order_spikes_and_the_newest_point():
    n = 100_000
    ys = [0.0] * n
    ys[12_345] = 9.0
    ys[54_321] = -9.0
    xs, out = thin(list(range(n)), ys, 400)
    assert len(xs) <= 801 and xs == sorted(xs)
    assert 9.0 in out and -9.0 in out and xs[-1] == n - 1
