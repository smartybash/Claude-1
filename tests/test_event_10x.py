"""event_10x: market digitals, position payoffs, event windows, split handling."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import event_10x as E  # noqa: E402


def leg(k, side, mark, ask=None, bid=None, oi=500):
    return {"strike": k, "type": side, "mark": mark, "ask": ask if ask is not None else mark,
            "bid": bid if bid is not None else mark, "oi": oi,
            "implied_volatility": 0.5, "delta": 0.0}


def test_commission_tiers():
    assert E.commission(0.03) == 0.25
    assert E.commission(0.07) == 0.50
    assert E.commission(0.10) == 0.65


def test_call_spread_price_is_the_digital_probability():
    # C(100)=3.0, C(110)=2.0 -> a $1 digital above 105 costs 0.10
    chain = [leg(100, "call", 3.0), leg(110, "call", 2.0), leg(120, "call", 1.5)]
    assert E.digital_prob(chain, 105, "call") == pytest.approx(0.10)
    assert E.digital_prob(chain, 115, "call") == pytest.approx(0.05)


def test_put_digital_mirrors_calls():
    chain = [leg(80, "put", 0.5), leg(90, "put", 1.5), leg(100, "put", 4.0)]
    assert E.digital_prob(chain, 85, "put") == pytest.approx(0.10)


def test_penny_noise_cannot_create_a_rising_call_digital():
    # 44 marked 0.08, 44.5 marked 0.04: the raw spread claims 8% above 44.25
    # while 43.5-44 says 0%. A call digital can't rise with strike.
    chain = [leg(43.5, "call", 0.08), leg(44.0, "call", 0.08),
             leg(44.5, "call", 0.04), leg(45.0, "call", 0.04)]
    p1 = E.digital_prob(chain, 43.75, "call")
    p2 = E.digital_prob(chain, 44.25, "call")
    p3 = E.digital_prob(chain, 44.75, "call")
    assert p1 >= p2 >= p3
    # raw [0, 0.08, 0] -> the violating first pair pools to 0.04 each
    assert (p1, p2, p3) == (pytest.approx(0.04), pytest.approx(0.04), pytest.approx(0.0))


def test_isotonic_leaves_monotone_input_alone():
    assert E._isotonic([0.3, 0.2, 0.1], [1, 1, 1], increasing=False) == [0.3, 0.2, 0.1]


def test_digital_off_chain_is_none():
    chain = [leg(100, "call", 3.0), leg(110, "call", 2.0)]
    assert E.digital_prob(chain, 200, "call") is None


def test_naked_position_sizing_and_target_level():
    p = E.Position("x", "call", 100.0, None, 1.00, E.commission(1.00), E.EXIT_FEE)
    assert p.n == int(10_000 // 100.65)
    lvl = p.level()
    assert p.value(lvl) == pytest.approx(E.TARGET, rel=1e-6)
    assert p.value(99.0) == 0.0


def test_vertical_payoff_is_capped_at_width():
    p = E.Position("s", "call", 100.0, 110.0, 1.00, 1.30, 1.30)
    assert p.value(150.0) == pytest.approx(p.value(110.0))
    assert p.max_pay == pytest.approx(p.n * (10 * 100 - 1.30))


def test_vertical_below_target_has_no_level():
    # debit 5 on a 10-wide spread: 2x max, can never reach 10x
    p = E.Position("s", "call", 100.0, 110.0, 5.00, 1.30, 1.30)
    assert p.level() is None


def test_put_position_levels_below_strike():
    p = E.Position("p", "put", 100.0, None, 0.50, E.commission(0.50), E.EXIT_FEE)
    assert p.level() < 100.0
    assert p.value(p.level()) == pytest.approx(E.TARGET, rel=1e-6)


def test_window_returns_aligns_post_and_pre_market_reactions():
    dates = [f"2026-01-{d:02d}" for d in range(5, 10)] + [f"2026-01-{d:02d}" for d in range(12, 17)]
    close = [100, 101, 102, 110, 111, 112, 113, 114, 115, 116]
    # post-market report on the 7th -> reaction session is the 8th (index 3)
    post = E.window_returns(dates, close, [("2026-01-07", "post")], pre=1, post=0)
    assert post == [("2026-01-07", pytest.approx(110 / 102 - 1))]
    # pre-market report on the 8th -> reaction is the 8th itself: same window
    pre = E.window_returns(dates, close, [("2026-01-08", "pre")], pre=1, post=0)
    assert pre[0][1] == pytest.approx(110 / 102 - 1)


def test_sessions_between_skips_weekends():
    assert E.sessions_between("2026-09-29", "2026-10-02") == 3   # Tue -> Fri
    assert E.sessions_between("2026-10-02", "2026-10-05") == 1   # Fri -> Mon


def test_split_detection_back_adjusts(tmp_path):
    rows = "timestamp,open,high,low,close,volume\n" + "\n".join([
        "2020-01-02,100,100,100,100,1", "2020-01-03,102,102,102,102,1",
        "2020-01-06,51,51,51,51,1",      # 2:1 split
        "2020-01-07,52,52,52,52,1"])
    f = tmp_path / "d.csv"
    f.write_text(rows)
    dates, close, splits = E.load_daily(str(f))
    assert splits == ["2020-01-06 2:1"]
    assert close[:2] == [pytest.approx(50), pytest.approx(51)]


def test_robust_edge_rejects_single_event_dependence():
    e = {"ev_all": 20_000, "ev_mod": 15_000, "ev_drop1": 12_000,
         "ev_mod_drop1": 3_000, "boot": 0.95}
    assert not E.robust_edge(e)
    e["ev_mod_drop1"] = 11_000
    assert E.robust_edge(e)
