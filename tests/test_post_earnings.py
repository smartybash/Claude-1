"""post-announcement rules: the pre-registered 10:30 classification and data coverage."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import post_earnings_intraday as P  # noqa: E402

TYP = 0.06  # typical move 6% -> qualifying gap >= 3%


@pytest.mark.parametrize("g,f,p,state", [
    (0.02, 0.01, 0.90, "-"),          # gap below 0.5 x typical
    (0.05, 0.01, 0.80, "CONFIRM"),    # gap up, first hour up, near the high
    (0.05, 0.01, 0.70, "CONFIRM"),    # boundary is inclusive
    (0.05, 0.01, 0.69, "MIXED"),      # up but mid-range
    (0.05, -0.01, 0.20, "REJECT"),    # gap up, first hour down, near the low
    (0.05, -0.01, 0.50, "MIXED"),
    (-0.05, -0.01, 0.30, "CONFIRM"),  # gap down mirrored
    (-0.05, 0.01, 0.75, "REJECT"),
    (-0.05, 0.00, 0.10, "MIXED"),     # flat first hour is neither
])
def test_classify(g, f, p, state):
    assert P.classify(g, f, p, TYP) == state


def test_micron_oct_1_does_not_qualify():
    # MU 2026-10-01: gap -1.12% against a 9.06% typical move
    assert P.classify(-0.0112, -0.0200, 0.19, 0.0906) == "-"


def test_intraday_sample_is_complete():
    evs = [P.measure(*e) for e in P.reaction_events()]
    assert len(evs) == 152
    assert not [e for e in evs if "missing" in e]


def test_preregistration_is_committed():
    text = (ROOT / "reports/post_earnings_preregistration.md").read_text()
    assert "P ≥ 0.70" in text and "0.5 × typical" in text
