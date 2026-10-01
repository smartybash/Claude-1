"""Every Vol Desk rule and exception, pinned.

Base fixture: a name that clears all five filters with spot above pTrans.
Each test breaks exactly one rule (or exercises exactly one exception)
and checks the engine responds as specced.
"""

import pytest

from vol_desk import (
    BLOCKED, CONFIRMED, PENDING, WAIT,
    EXIT_NEXT_OPEN, EXIT_NOW, EXIT_STALL, EXIT_TIME, HOLD, T1_DECISION,
    T2_HIT, WATCH,
    B_CONTINUATION, P2P,
    Position, ScreenRow,
    approve, continuation_eligible, hard_cap_hit, lock_and_ride,
    mark_session, open_trigger, read_gates, screen, size_factor, take_t1,
)


def row(**over) -> ScreenRow:
    """Grade 10, db_change 0.60, spot 102 vs pTrans 100, +GEX 110 (R/R 4.0),
    COTMP 97 (cushion ~5.2%), no spike-crash: passes everything."""
    base = dict(
        symbol="TEST", spot=102.0,
        p_trans=100.0, n_trans=95.0, plus_gex=110.0, cotmp=97.0,
        grade=10, db_change=0.60, delta_balance=0.85, delta_balance_prior=0.25,
    )
    base.update(over)
    return ScreenRow(**base)


# ---------------------------------------------------------------- filters

def test_base_setup_is_confirmed():
    assert screen(row()).status == CONFIRMED

def test_grade_8_is_a_hard_block():
    assert screen(row(grade=8)).status == BLOCKED
    assert "grade" in screen(row(grade=8)).failed_filters()

def test_grade_9_clears_the_bar():
    assert screen(row(grade=9)).status == CONFIRMED

def test_db_change_below_050_blocks():
    assert screen(row(db_change=0.49)).status == BLOCKED

def test_db_change_at_050_passes():
    assert screen(row(db_change=0.50)).status == CONFIRMED

def test_grade11_deep_gets_030_db_threshold():
    assert screen(row(grade=11, deep=True, db_change=0.30)).status == CONFIRMED
    assert screen(row(grade=11, deep=True, db_change=0.29)).status == BLOCKED

def test_deep_threshold_needs_both_grade11_and_deep():
    assert screen(row(grade=11, deep=False, db_change=0.30)).status == BLOCKED

def test_sustained_pegged_delta_is_exempt_from_db_filter():
    r = row(delta_balance=1.00, delta_balance_prior=1.00, db_change=0.0)
    assert screen(r).status == CONFIRMED

def test_one_pegged_session_is_not_sustained():
    r = row(delta_balance=1.00, delta_balance_prior=0.70, db_change=0.0)
    assert screen(r).status == BLOCKED

def test_cotmp_cushion_below_2pct_blocks():
    # spot 102, cushion 1.9% -> cotmp = 102/1.019
    assert screen(row(cotmp=102 / 1.019)).status == BLOCKED

def test_cotmp_cushion_at_2pct_passes():
    assert screen(row(cotmp=102 / 1.021)).status == CONFIRMED

def test_deep_gets_1pct_cushion_exception():
    r = row(grade=11, deep=True, cotmp=102 / 1.012)
    assert screen(r).status == CONFIRMED

def test_high_db_change_gets_1pct_cushion_exception():
    r = row(db_change=1.20, cotmp=102 / 1.012)
    assert screen(r).status == CONFIRMED
    r2 = row(db_change=0.60, cotmp=102 / 1.012)
    assert screen(r2).status == BLOCKED

def test_spike_crash_blocks_regardless_of_everything_else():
    r = row(grade=11, deep=True, db_change=2.0, spike_crash=True)
    assert screen(r).status == BLOCKED
    assert "spike_crash" in screen(r).failed_filters()

def test_rr_below_2_blocks():
    # spot 104: upside 6, downside 4 -> R/R 1.5
    assert screen(row(spot=104.0)).status == BLOCKED

def test_rr_at_2_passes():
    # spot 103.33: upside 6.67, downside 3.33 -> R/R ~2.0
    assert screen(row(spot=103.32)).status == CONFIRMED


# --------------------------------------------------------------- statuses

def test_pending_within_half_pct_below_ptrans():
    assert screen(row(spot=99.6)).status == PENDING

def test_wait_below_the_pending_band():
    assert screen(row(spot=99.0)).status == WAIT

def test_pending_with_failed_filter_is_blocked():
    assert screen(row(spot=99.6, grade=8)).status == BLOCKED


# ----------------------------------------------------------- open trigger

def test_trigger_fires_on_5min_close_above_ptrans():
    assert open_trigger(row(spot=99.6), first_5min_close=100.4)

def test_trigger_rejects_close_at_or_below_ptrans():
    assert not open_trigger(row(spot=99.6), first_5min_close=100.0)
    assert not open_trigger(row(spot=102.0), first_5min_close=99.5)

def test_trigger_rechecks_rr_at_the_confirming_close():
    # close at 104 -> R/R 1.5, fails even though the level broke
    assert not open_trigger(row(spot=99.6), first_5min_close=104.0)


# ------------------------------------------------------------------ exits

def pos(**over) -> Position:
    base = dict(symbol="TEST", entry=101.0, p_trans=100.0, n_trans=95.0,
                t1=110.0, t2=118.0)
    base.update(over)
    return Position(**base)

def test_hold_confirmed_above_ptrans():
    assert mark_session(pos(), 105.0).action == HOLD

def test_watch_between_ntrans_and_ptrans():
    assert mark_session(pos(), 98.0).action == WATCH

def test_stop1_close_below_ntrans_exits_next_open():
    assert mark_session(pos(), 94.5).action == EXIT_NEXT_OPEN

def test_stop2_hard_cap_below_ptrans():
    p = pos()
    assert hard_cap_hit(p, 90.9)            # -10% and below pTrans
    assert mark_session(p, 90.9).action != HOLD

def test_stop2_needs_below_ptrans():
    p = pos(entry=112.0, p_trans=100.0)     # -10% = 100.8, still above pTrans
    assert not hard_cap_hit(p, 100.8)

def test_stop3_day7_under_half_progress_exits():
    # staircase that dodges the stall rule (a 12% step every 3rd session)
    # but sits at only 36% progress on day 7
    p = pos()
    closes = [102.08, 102.08, 102.08, 103.16, 103.16, 103.16, 104.24]
    actions = [mark_session(p, c).action for c in closes]
    assert actions[:6] == [HOLD] * 6
    assert actions[-1] == EXIT_TIME

def test_stop3_day7_with_progress_holds():
    # same shape but at 60% progress by day 7: the time stop passes
    p = pos()
    closes = [102.8, 102.8, 102.8, 104.6, 104.6, 104.6, 106.4]
    actions = [mark_session(p, c).action for c in closes]
    assert actions[-1] == HOLD

def test_stop4_three_stalled_sessions_exit():
    p = pos()
    mark_session(p, 105.0)                   # +44% day 1: fine
    mark_session(p, 105.2)                   # +2%: stall 1
    mark_session(p, 105.4)                   # +2%: stall 2
    assert mark_session(p, 105.5).action == EXIT_STALL  # stall 3

def test_stop4_resets_on_a_strong_session():
    p = pos()
    mark_session(p, 101.2)                   # stall 1
    mark_session(p, 101.4)                   # stall 2
    mark_session(p, 103.0)                   # +18%: streak broken
    assert mark_session(p, 103.2).action == HOLD


# ----------------------------------------------------------------- T1/T2

def test_t1_hit_demands_a_decision():
    p = pos()
    assert mark_session(p, 110.5).action == T1_DECISION
    assert p.t1_hit

def test_take_t1_banks_it():
    p = pos()
    mark_session(p, 110.5)
    assert take_t1(p).action == EXIT_NOW

def test_cannot_ride_t2_without_t1_first():
    with pytest.raises(ValueError):
        lock_and_ride(pos())

def test_lock_and_ride_needs_a_t2_level():
    p = pos(t2=None)
    mark_session(p, 110.5)
    with pytest.raises(ValueError):
        lock_and_ride(p)

def test_locked_stop_exits_at_entry():
    p = pos()
    mark_session(p, 110.5)
    lock_and_ride(p)
    assert p.stop == p.entry
    assert mark_session(p, 100.5).action == EXIT_NOW

def test_t2_hit_banks_it():
    p = pos()
    mark_session(p, 110.5)
    lock_and_ride(p)
    assert mark_session(p, 118.5).action == T2_HIT


# ------------------------------------------------------------------ regime

def gates(basket=0.008, bulls=400, bears=100, vix=-0.5):
    return read_gates(spy_pct=basket, qqq_pct=0.0, bull_names=bulls,
                      bear_names=bears, vix_dealer_delta=vix)

def test_all_three_gates_pass():
    assert gates().count == 3

def test_basket_gate_needs_more_than_half_pct():
    assert not gates(basket=0.004).basket
    assert read_gates(0.0, 0.006, 400, 100, -0.5).basket  # QQQ alone is enough

def test_bull_bear_gate_needs_above_3_to_1():
    assert not gates(bulls=300, bears=100).bull_bear     # exactly 3.0 fails
    assert gates(bulls=301, bears=100).bull_bear

def test_vix_gate_needs_negative_dealer_delta():
    assert not gates(vix=0.2).vix

def test_p2p_runs_at_2_of_3_only_on_strong_setups():
    g = gates(vix=0.2)  # 2/3
    assert not approve(P2P, g)
    assert approve(P2P, g, strong_setup=True)
    assert approve(P2P, gates())            # 3/3 needs no exception

def test_continuation_requires_full_3_of_3():
    assert not approve(B_CONTINUATION, gates(vix=0.2), strong_setup=True)
    assert approve(B_CONTINUATION, gates())

def test_hyg_divergence_halves_new_entry_size():
    assert size_factor(hyg_bear=True, equities_bullish=True) == 0.5
    assert size_factor(hyg_bear=False, equities_bullish=True) == 1.0
    assert size_factor(hyg_bear=True, equities_bullish=False) == 1.0


# --------------------------------------------------------- B Continuation

def test_continuation_needs_minervini_100():
    assert continuation_eligible(row(minervini=105))
    assert not continuation_eligible(row(minervini=95))
    assert not continuation_eligible(row())              # no score, no entry

def test_continuation_still_respects_the_filters():
    assert not continuation_eligible(row(minervini=120, spike_crash=True))
