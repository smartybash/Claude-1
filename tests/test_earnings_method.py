"""earnings_method: no look-ahead, timing resolution, splits, statistics."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vol_desk import earnings_method as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def series(closes, vols=None, opens=None, sym="X"):
    n = len(closes)
    # strictly increasing unique date keys are all the code relies on
    dates = [f"2000-01-01+{i:05d}" for i in range(n)]
    return M.Series(sym, dates, opens or list(closes), list(closes), vols or [1e6] * n)


def truncated(s: M.Series, upto: int) -> M.Series:
    return M.Series(s.sym, s.dates[:upto + 1], s.open[:upto + 1], s.close[:upto + 1],
                    s.volume[:upto + 1])


@pytest.mark.parametrize("sym", ["MU", "NKE"])
def test_drivers_use_no_future_data(sym):
    """Drivers at the decision close are identical whether or not the
    series continues past it — the decisive look-ahead check."""
    spy = M.load_series(ROOT / "data/daily/SPY.json", "SPY")
    s = M.load_series(ROOT / f"data/daily/{sym}.json", sym)
    res = [x for x in M.resolve_reactions(s, spy, M.load_earnings(ROOT / f"data/earnings/{sym}.json"))
           if x.r is not None and x.r >= 65]
    checked = 0
    for k in range(10, len(res), 9):
        r = res[k].r
        d = r - 1
        prior = [x.r for x in res[max(0, k - 8):k]]
        sur = [x.surprise for x in res[max(0, k - 8):k]]
        full = M.drivers(s, spy, d, prior, sur)
        cut = M.drivers(truncated(s, d), truncated(spy, spy.idx[s.dates[d]]), d, prior, sur)
        assert full == cut, f"{sym} {s.dates[d]}"
        checked += 1
    assert checked >= 5


def test_resolver_keeps_label_unless_volume_clearly_disagrees():
    spy = series([100.0] * 200)
    vols = [1e6] * 200
    vols[101] = 3e6   # post-market label -> reaction 101, modest spike
    vols[100] = 3.5e6  # report day only slightly bigger: label must stand
    s = series([100.0] * 200, vols)
    r = M.resolve_reactions(s, spy, [(s.dates[100], "post", 5.0)])[0]
    assert r.r == 101 and not r.relabelled


def test_resolver_relabels_on_clear_volume_evidence():
    spy = series([100.0] * 200)
    vols = [1e6] * 200
    vols[100] = 8e6   # labelled post-market, but the report day is the spike
    s = series([100.0] * 200, vols)
    r = M.resolve_reactions(s, spy, [(s.dates[100], "post", 5.0)])[0]
    assert r.r == 100 and r.relabelled


def test_split_confirmed_with_large_same_day_move(tmp_path):
    # 5:1 split on a day the stock also rose 12.6% (TSLA, 2020-08-31)
    rows = ["timestamp,open,high,low,close,volume",
            "2020-08-27,2200,1,1,2238.75,1", "2020-08-28,2200,1,1,2213.40,1",
            "2020-08-31,444,1,1,498.32,5", "2020-09-01,500,1,1,475.05,5"]
    f = tmp_path / "TSLA.json"
    f.write_text(json.dumps({"result": "\n".join(rows)}))
    s = M.load_series(f, "TSLA")
    assert any(x.startswith("2020-08-31 5") for x in s.splits)
    assert s.close[1] == pytest.approx(2213.40 / 5)


def test_binomial_tails():
    assert M.binom_p_greater(0, 10, 0.5) == pytest.approx(1.0)
    assert M.binom_p_greater(10, 10, 0.5) == pytest.approx(0.5 ** 10)
    assert M.binom_p(5, 10, 0.5) == pytest.approx(1.0)
    assert M.binom_p(9, 10, 0.5) < 0.05


def test_frozen_model_and_preregistration_are_committed():
    model = json.loads((ROOT / "reports/earnings_model_v1_frozen.json").read_text())
    assert model["selected"] == ["runup", "prior_reaction"]
    assert all(model["signs"][d] == -1 for d in model["selected"])
    assert (ROOT / "reports/earnings_preregistration.md").exists()
