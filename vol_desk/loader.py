"""CSV loader for the evening gamma screen -> ScreenRow records.

The screen export changes shape depending on which platform produced it, so
the loader is alias-tolerant: headers are normalized (lowercase, spaces and
hyphens to underscores, '+' -> 'plus_') and matched against known aliases.
`pTrans`, `p-trans`, `Pos Trans` all land on ``p_trans``; `+GEX`, `plusGEX`,
`GEX+` all land on ``plus_gex``; and so on.

Grade handling: a cell like ``11 DEEP`` sets grade=11 and the DEEP flag; a
separate deep/spike-crash column also works (y/yes/true/1/x all read as
true). If ``db_change`` is missing it is computed from delta balance minus
the prior session's.

Only stdlib csv — the package stays dependency-free.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import ScreenRow

# canonical field -> accepted header aliases (after normalization)
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "ticker", "sym", "name"),
    "spot": ("spot", "price", "last", "close", "px", "underlying"),
    "p_trans": ("p_trans", "ptrans", "pos_trans", "positive_transition", "p_transition"),
    "n_trans": ("n_trans", "ntrans", "neg_trans", "negative_transition", "n_transition"),
    "plus_gex": ("plus_gex", "plusgex", "gexplus", "pos_gex", "posgex", "gex_plus", "t1"),
    "zero_gex": ("zero_gex", "zerogex", "gex0", "0gex", "zero"),
    "cotmp": ("cotmp", "cotm_p", "center_of_put_mass", "put_mass"),
    "cotmc": ("cotmc", "cotm_c", "center_of_call_mass", "call_mass"),
    "t2": ("t2", "target2", "t2_level", "next_level"),
    "grade": ("grade", "score", "rules", "structural_grade"),
    "deep": ("deep", "is_deep"),
    "delta_balance": ("delta_balance", "db", "deltabalance", "dealer_delta", "delta_bal"),
    "delta_balance_prior": ("delta_balance_prior", "prior_db", "db_prior", "prev_db",
                            "db_prev", "prior_delta", "prior_delta_balance"),
    "db_change": ("db_change", "db_chg", "dbchg", "delta_change", "db_delta"),
    "spike_crash": ("spike_crash", "spikecrash", "spike", "spike_high"),
    "minervini": ("minervini", "mms", "minervini_score", "momentum", "momentum_score"),
    "oi_depth": ("oi_depth", "oi", "open_interest_depth", "oi_score"),
}

REQUIRED = ("symbol", "spot", "p_trans", "n_trans", "plus_gex", "cotmp", "grade")

_TRUE = {"y", "yes", "true", "t", "1", "x", "deep"}


def _norm(header: str) -> str:
    h = header.strip().lower().replace("+", "plus_")
    h = re.sub(r"[\s\-./]+", "_", h)
    return re.sub(r"_+", "_", h).strip("_")


def _map_headers(headers: list[str]) -> dict[str, str]:
    """raw header -> canonical field, for every header we recognize."""
    lookup = {alias: field for field, aliases in COLUMN_ALIASES.items() for alias in aliases}
    return {raw: lookup[_norm(raw)] for raw in headers if _norm(raw) in lookup}


def _num(cell: str | None) -> float | None:
    if cell is None:
        return None
    s = cell.strip().replace("$", "").replace(",", "").replace("%", "")
    if not s or s.lower() in ("na", "n/a", "-", "none", "null"):
        return None
    return float(s)


def _flag(cell: str | None) -> bool:
    return bool(cell) and cell.strip().lower() in _TRUE


def _grade(cell: str | None) -> tuple[int, bool]:
    """Parse '9', '11', or '11 DEEP' -> (grade, deep)."""
    if not cell or not cell.strip():
        return 0, False
    s = cell.strip()
    deep = "deep" in s.lower()
    m = re.search(r"\d+", s)
    return (int(m.group()) if m else 0), deep


def load_gamma_screen(path: str | Path) -> list[ScreenRow]:
    """Load the evening gamma screen CSV. Raises on missing required columns."""
    path = Path(path)
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: empty file")
        colmap = _map_headers(list(reader.fieldnames))
        have = set(colmap.values())
        missing = [f for f in REQUIRED if f not in have]
        if missing:
            raise ValueError(
                f"{path}: missing required column(s) {missing}; "
                f"recognized headers: {sorted(have)}")
        if "db_change" not in have and not {"delta_balance", "delta_balance_prior"} <= have:
            raise ValueError(
                f"{path}: need a db_change column, or delta_balance plus its prior "
                f"session to compute it")

        rows = []
        for raw in reader:
            rec = {field: raw.get(header) for header, field in colmap.items()}
            if not (rec.get("symbol") or "").strip():
                continue  # blank line
            grade, deep_in_grade = _grade(rec.get("grade"))
            db = _num(rec.get("delta_balance"))
            db_prior = _num(rec.get("delta_balance_prior"))
            db_change = _num(rec.get("db_change"))
            if db_change is None:
                db_change = (db or 0.0) - (db_prior or 0.0)
            rows.append(ScreenRow(
                symbol=rec["symbol"].strip().upper(),
                spot=_num(rec["spot"]),
                p_trans=_num(rec["p_trans"]),
                n_trans=_num(rec["n_trans"]),
                plus_gex=_num(rec["plus_gex"]),
                cotmp=_num(rec["cotmp"]),
                zero_gex=_num(rec.get("zero_gex")),
                cotmc=_num(rec.get("cotmc")),
                t2=_num(rec.get("t2")),
                grade=grade,
                deep=deep_in_grade or _flag(rec.get("deep")),
                delta_balance=db if db is not None else 0.0,
                delta_balance_prior=db_prior,
                db_change=db_change,
                spike_crash=_flag(rec.get("spike_crash")),
                minervini=_num(rec.get("minervini")),
                oi_depth=_num(rec.get("oi_depth")),
            ))
        return rows
