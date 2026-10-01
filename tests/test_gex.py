"""GEX level engine: sign conventions, level identification, rescaling."""

import pytest

from vol_desk.gex import Leg, bs_gamma, levels, net_gex, rescale


def chain(call_strikes: dict[float, int], put_strikes: dict[float, int], iv=0.20):
    return ([Leg(k, True, oi, iv) for k, oi in call_strikes.items()]
            + [Leg(k, False, oi, iv) for k, oi in put_strikes.items()])


def test_bs_gamma_peaks_near_the_money():
    g_atm = bs_gamma(100, 100, 0.2, 30 / 365)
    assert g_atm > bs_gamma(100, 120, 0.2, 30 / 365)
    assert g_atm > bs_gamma(100, 80, 0.2, 30 / 365)


def test_call_heavy_book_is_positive_gamma():
    legs = chain({100: 10000}, {100: 100})
    assert net_gex(100, legs, 30 / 365, 100) > 0


def test_put_heavy_book_is_negative_gamma():
    legs = chain({100: 100}, {100: 10000})
    assert net_gex(100, legs, 30 / 365, 100) < 0


def test_plus_gex_is_the_dominant_call_strike():
    legs = chain({105: 500, 110: 9000, 120: 300}, {90: 1000})
    lv = levels(100, legs, 30)
    assert lv["plus_gex"] == 110


def test_t2_is_the_next_positive_strike_above_t1():
    legs = chain({110: 9000, 115: 4000, 120: 100}, {90: 1000})
    lv = levels(100, legs, 30)
    assert lv["plus_gex"] == 110 and lv["t2"] == 115


def test_transition_band_brackets_the_flip():
    # puts dominate below, calls above -> flip sits between them
    legs = chain({105: 8000, 110: 6000}, {95: 8000, 90: 6000})
    lv = levels(100, legs, 30)
    assert lv["zero_gex"] is not None
    assert lv["n_trans"] < lv["zero_gex"] < lv["p_trans"]


def test_one_signed_book_has_no_transitions():
    legs = chain({100: 5000, 110: 5000}, {})
    lv = levels(100, legs, 30)
    assert lv["zero_gex"] is None and lv["p_trans"] is None


def test_centers_of_mass_are_oi_weighted():
    legs = chain({110: 1000, 120: 1000}, {80: 3000, 90: 1000})
    lv = levels(100, legs, 30)
    assert lv["cotmc"] == pytest.approx(115.0)
    assert lv["cotmp"] == pytest.approx((80 * 3000 + 90 * 1000) / 4000)


def test_cushion_measures_spot_above_put_mass():
    legs = chain({110: 1000}, {90: 1000})
    lv = levels(99, legs, 30)
    assert lv["cushion"] == pytest.approx((99 - 90) / 90)


def test_multiplier_scales_dollar_gamma_linearly():
    legs = chain({100: 1000}, {})
    a = net_gex(100, legs, 30 / 365, 100)
    b = net_gex(100, legs, 30 / 365, 20)
    assert b == pytest.approx(a * 0.2)


def test_rescale_converts_prices_and_preserves_ratios():
    legs = chain({105: 8000, 110: 6000}, {95: 8000, 90: 6000})
    lv = levels(100, legs, 30)
    out = rescale(lv, 41.5)
    assert out["spot"] == pytest.approx(100 * 41.5)
    assert out["plus_gex"] == pytest.approx(lv["plus_gex"] * 41.5)
    assert out["cushion"] == lv["cushion"]          # scale-invariant
    assert out.get("rr") == lv.get("rr")
