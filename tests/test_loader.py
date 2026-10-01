"""Loader: header aliasing, grade/flag parsing, derived db_change."""

import pytest

from vol_desk.loader import load_gamma_screen


def write(tmp_path, text):
    p = tmp_path / "screen.csv"
    p.write_text(text)
    return p


def test_aliased_headers_and_grade_deep(tmp_path):
    p = write(tmp_path,
        "Ticker,Last,pTrans,nTrans,+GEX,COTMP,Grade,DB,Prior DB,DB Chg,Spike-Crash\n"
        "nvda,172,170,163,181,170,11 DEEP,0.71,0.36,0.35,\n"
        "amd,$128,126,120,138,123,11,0.95,-0.45,1.40,Y\n")
    rows = load_gamma_screen(p)
    nvda, amd = rows
    assert nvda.symbol == "NVDA"          # upcased
    assert nvda.grade == 11 and nvda.deep
    assert nvda.plus_gex == 181 and nvda.p_trans == 170
    assert not nvda.spike_crash
    assert amd.spot == 128.0              # '$' stripped
    assert amd.grade == 11 and not amd.deep
    assert amd.spike_crash                # 'Y' is true


def test_db_change_computed_from_prior_when_missing(tmp_path):
    p = write(tmp_path,
        "Symbol,Spot,p_trans,n_trans,plus_gex,cotmp,grade,delta_balance,prior_db\n"
        "AAPL,232,228,219,245,222,10,0.82,0.22\n")
    row = load_gamma_screen(p)[0]
    assert row.db_change == pytest.approx(0.60)
    assert row.delta_balance_prior == 0.22


def test_missing_required_column_raises(tmp_path):
    p = write(tmp_path, "Symbol,Spot,grade\nAAPL,232,10\n")
    with pytest.raises(ValueError, match="missing required"):
        load_gamma_screen(p)


def test_missing_db_info_raises(tmp_path):
    p = write(tmp_path,
        "Symbol,Spot,p_trans,n_trans,plus_gex,cotmp,grade\n"
        "AAPL,232,228,219,245,222,10\n")
    with pytest.raises(ValueError, match="db_change"):
        load_gamma_screen(p)


def test_blank_rows_skipped_and_optionals_none(tmp_path):
    p = write(tmp_path,
        "Symbol,Spot,p_trans,n_trans,plus_gex,cotmp,grade,db_chg,minervini\n"
        "AAPL,232,228,219,245,222,10,0.6,\n"
        ",,,,,,,,\n")
    rows = load_gamma_screen(p)
    assert len(rows) == 1
    assert rows[0].minervini is None


def test_example_screen_loads(tmp_path):
    rows = load_gamma_screen("data/gamma_screen_example.csv")
    assert len(rows) == 11
    msft = next(r for r in rows if r.symbol == "MSFT")
    assert msft.sustained                 # pegged at 1.00 two sessions
