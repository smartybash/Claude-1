"""Cell-size arithmetic ONLY. No outcome is read, no R is touched."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/Claude-1/scripts/orderflow')
import rp008_stage0 as A

lib = {}
lib.update(A.orb_and_pullback())
lib.update(A.ib_family_times())
lib.update(A.orb_fib_times())
cs,_ = A.compression_sets(); lib.update(cs)
lib.update(A.ib_midpoint_pullback())

# causal prior-session realised volatility, per session (no same-day data)
import or_height as OH
S1,_ = OH.build("data/intraday_long/QQQ_1m.parquet", 1)
days = sorted(S1)
rv = {}
prev = None
for d in days:
    s = S1[d]
    c = np.asarray(s["cl"], float)
    r = np.diff(np.log(c))
    v = float(np.std(r)) if len(r) > 10 else np.nan
    rv[d] = prev                  # CAUSAL: yesterday's rv labels today
    prev = v
RV = pd.Series(rv)
# rolling causal terciles over the prior 250 labelled sessions
ser = RV.copy()
lab = {}
vals = ser.to_numpy(float); idx = list(ser.index)
for i,d in enumerate(idx):
    if i < 60 or not np.isfinite(vals[i]): lab[d]=None; continue
    hist = vals[max(0,i-250):i]; hist = hist[np.isfinite(hist)]
    if len(hist) < 60: lab[d]=None; continue
    lo,hi = np.percentile(hist,[33.3,66.7])
    lab[d] = "LO" if vals[i]<lo else ("HI" if vals[i]>hi else "MID")
LAB = pd.Series(lab)

print("causal prior-session RV tercile coverage: %d of %d sessions labelled"
      % (int(LAB.notna().sum()), len(LAB)))
print(LAB.value_counts().to_string())
print()
print("CELL SIZES  strategy x (time block) x (causal prior-session vol tercile)")
print("%-32s %-22s %6s %6s %6s %6s" % ("strategy","block","LO","MID","HI","all"))
rows=[]
for name,T in lib.items():
    if "m" not in T or T["m"].isna().all(): continue
    T = T.dropna(subset=["m"]).copy()
    T["blk"] = T["m"].apply(A.tod_of)
    T["vol"] = [LAB.get(pd.Timestamp(d).date() if not isinstance(d,str) else d, None) for d in T["day"]]
    if T["vol"].isna().all():
        T["vol"] = [LAB.get(d, None) for d in T["day"]]
    for blk,_a,_b in A.TOD:
        g = T[T.blk==blk]
        if not len(g): continue
        c = g["vol"].value_counts()
        rows.append(dict(strategy=name, block=blk, LO=int(c.get("LO",0)),
                         MID=int(c.get("MID",0)), HI=int(c.get("HI",0)), all=len(g)))
        print("%-32s %-22s %6d %6d %6d %6d" % (name,blk,c.get("LO",0),c.get("MID",0),c.get("HI",0),len(g)))
pd.DataFrame(rows).to_csv('/tmp/claude-0/-home-user-Claude-1/53a4adb9-543d-5460-95dd-0cda0b53172f/scratchpad/cells.csv',index=False)
