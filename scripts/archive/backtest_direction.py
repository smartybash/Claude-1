"""Is there a DIRECTION edge in the options-chain data? — honest test, no new fetches.

Everything we've shipped is a range/magnitude switch. This asks the harder
question: does anything in the chain predict next-day SIGN (up vs down)?

Data: gex_history.jsonl (spot, net_gex, gamma_flip, call_wall, put_wall,
dealer_delta per QQQ session) + QQQ daily OHLC. Chain OI is as-of session D
close -> it sets D+1's open, so every feature(D) is tested on D+1's realized
open->close return.

Hypotheses (each a simple, mechanical directional rule):
  H1 pin-reversion  : POSITIVE gamma -> price drawn to flip. Predict up if spot<flip.
  H2 flip-momentum  : NEGATIVE gamma -> moves extend away from flip. Predict
                      continuation in the direction spot is already off the flip.
  H3 wall-channel   : position of spot in [put_wall, call_wall]. Near call wall
                      -> fade down; near put wall -> fade up (POSITIVE gamma).
  H4 dealer-delta   : sign of dealer delta -> direction (re-check, was null).
  H5 gap-persist    : baseline non-chain control (does yesterday's move persist?).

Scoring: hit-rate P(correct sign), mean signed return IN THE PREDICTED direction
(so a working rule is positive), Welch t of predicted-dir returns vs 0, and
split-half hit-rate. n~30 -> directional read, not proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def qqq_daily():
    r = json.loads((ROOT / "data" / "qqq_daily_5y.json").read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime([t[:10] for t in r["time"]]))
    return df[~df.index.duplicated(keep="last")].sort_index()


def tstat(x):
    x = np.array(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return x.mean() / (x.std(ddof=1) / len(x) ** 0.5)


def main():
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gex = [g for g in gex if g["sym"] == "QQQ"]
    d = qqq_daily(); dates = list(d.index)
    rows = []
    for g in gex:
        day = pd.Timestamp(g["date"])
        after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]
        o, c = float(d.loc[nd, "open"]), float(d.loc[nd, "close"])
        ret = (c - o) / o * 100                      # next-day open->close %
        spot, flip = g["spot"], g["gamma_flip"]
        cw, pw = g["call_wall"], g["put_wall"]
        pos = (spot - pw) / (cw - pw) if cw > pw else 0.5   # 0=put wall,1=call wall
        rows.append({"date": g["date"], "ret": ret, "neg": g["net_gex"] < 0,
                     "above_flip": spot > flip, "pos": pos, "dd": g["dealer_delta"],
                     "prevret": (float(d.loc[day, "close"]) - float(d.loc[day, "open"])) /
                                float(d.loc[day, "open"]) * 100 if day in d.index else 0.0})
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    print(f"DIRECTION tests -> next-day open->close return (QQQ, n={len(df)})")
    print(f"base rate P(up) = {(df['ret']>0).mean():.0%}   mean ret {df['ret'].mean():+.3f}%\n")

    def report(name, pred, mask=None):
        """pred = predicted direction (+1/-1) Series; mask limits the sample."""
        sub = df if mask is None else df[mask]
        p = pred if mask is None else pred[mask]
        signed = sub["ret"] * p                        # return earned going pred way
        hit = (signed > 0).mean()
        mid = len(sub) // 2
        h1 = (signed.iloc[:mid] > 0).mean() if mid else float("nan")
        h2 = (signed.iloc[mid:] > 0).mean() if len(sub) - mid else float("nan")
        print(f"  {name:22s} n={len(sub):2d}  hit {hit:.0%}  mean {signed.mean():+.3f}%  "
              f"t {tstat(signed):+.2f}  split {h1:.0%}/{h2:.0%}")

    print("H1 pin-reversion (POSITIVE gamma only): predict toward flip")
    pos_mask = ~df["neg"]
    report("spot<flip -> up", np.where(df["above_flip"], -1, 1), pos_mask)

    print("\nH2 flip-momentum (NEGATIVE gamma only): predict away from flip (continuation)")
    neg_mask = df["neg"]
    report("off-flip -> continue", np.where(df["above_flip"], 1, -1), neg_mask)

    print("\nH3 wall-channel (POSITIVE gamma): fade toward center of [put_wall,call_wall]")
    report("upper half -> down", np.where(df["pos"] > 0.5, -1, 1), pos_mask)

    print("\nH4 dealer-delta sign -> direction (re-check)")
    report("delta>0 -> up", np.where(df["dd"] > 0, 1, -1))

    print("\nH5 control: yesterday's move persists (non-chain baseline)")
    report("prev up -> up", np.where(df["prevret"] > 0, 1, -1))

    # SKEW CONTROL: sample is down-skewed, so "predict down" wins for free. Judge
    # the positive-gamma mean-reversion rule per-leg (up-calls and down-calls must
    # BOTH beat their base rate) + a continuous correlation that can't be gamed by
    # always guessing the majority side.
    print("\n--- skew control for the positive-gamma mean-reversion edge ---")
    pg = df[~df["neg"]].copy()
    pg["dist"] = 0                                   # placeholder to keep columns
    up_calls = pg[~pg["above_flip"]]                 # rule says UP (spot below flip)
    dn_calls = pg[pg["above_flip"]]                  # rule says DOWN (spot above flip)
    print(f"  base rate this sample: P(up)={ (df['ret']>0).mean():.0%}  "
          f"'always-down' hit={ (df['ret']<0).mean():.0%}")
    print(f"  H1 UP-calls  (spot<flip): P(up)={ (up_calls['ret']>0).mean():.0%}  n={len(up_calls)}  "
          f"(needs > {(df['ret']>0).mean():.0%} base)")
    print(f"  H1 DOWN-calls(spot>flip): P(dn)={ (dn_calls['ret']<0).mean():.0%}  n={len(dn_calls)}  "
          f"(needs > {(df['ret']<0).mean():.0%} base)")
    # continuous: in positive gamma, further above flip -> more negative next return?
    pg2 = df[~df["neg"]]
    dist = None
    # rebuild distance from raw file for correlation
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gmap = {g["date"]: (g["spot"] - g["gamma_flip"]) / g["spot"] * 100 for g in gex if g["sym"] == "QQQ"}
    pgc = pg2.assign(distflip=pg2["date"].map(gmap))
    corr = pgc["distflip"].corr(pgc["ret"])
    print(f"  corr(spot-vs-flip distance, next-day return) in POS gamma = {corr:+.2f}  "
          f"(negative = mean-reversion to flip is real)")

    print("\nread: a real directional edge = hit >~60% AND t>~1.5 AND both split halves "
          ">50% AND both per-leg calls beat base rate AND corr has the right sign. "
          "Anything that only works on the majority side is just the sample's skew.")


if __name__ == "__main__":
    main()
