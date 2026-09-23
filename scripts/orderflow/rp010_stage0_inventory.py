"""RP-010 Stage 0 data inventory. COUNTS AND DISTRIBUTIONS ONLY. No outcomes."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/Claude-1/scripts/orderflow')
from tape import load_all, price_step, rth, is_full_session
import orderflow_core as OF, dataquality as DQ, sessioncal as SC

days = load_all()
fine = [(d,x) for d,x in sorted(days.items()) if price_step(x)<=1 and is_full_session(x)]
print("full 0.25 sessions:", len(fine))
rows=[]
for d,x in fine:
    s = rth(x).sort_values("time")
    tick = DQ.min_increment(s.price.to_numpy())
    agg = ''.join(sorted(set(s.aggressor.dropna().astype(str))))
    nulls = int(s.aggressor.isna().sum())
    # exclude first and last 5 minutes
    m = SC.minutes_after_open(s.time, day=pd.Timestamp(str(d)[:4]+'-'+str(d)[4:6]+'-'+str(d)[6:]).date(), clock="UTC")
    s = s.loc[(m>=5)&(m<385)]
    n30=0; vols=[]; trd=[]; imb=[]; tpk=[]
    for k,g in OF.windows(s, 30):
        a=OF.aggression(g); p=OF.progress(g, 0.25); i=OF.impact(a,p)
        n30+=1; vols.append(a["total"]); trd.append(a["n_trades"])
        if a["total"]>0: imb.append(a["imbalance"]); tpk.append(i["ticks_per_1k"])
    rows.append(dict(day=str(d), tick=tick, side_labels=agg, nulls=nulls, rth_prints=len(s),
                     w30=n30, med_vol=np.median(vols), med_trd=np.median(trd),
                     p90_vol=np.percentile(vols,90), zero_vol=float(np.mean(np.array(vols)==0)),
                     med_imb=np.median(imb), p90_imb=np.percentile(imb,90),
                     med_tpk=np.median(tpk), p10_tpk=np.percentile(tpk,10), p90_tpk=np.percentile(tpk,90)))
R=pd.DataFrame(rows)
pd.set_option('display.width',220)
print()
print("tick sizes:", R.tick.value_counts().to_dict())
print("aggressor labels:", R.side_labels.value_counts().to_dict(), " total nulls:", int(R.nulls.sum()))
print()
print("per session, 30-second NON-OVERLAPPING windows, 09:35-15:55:")
for c in ['w30','rth_prints','med_vol','p90_vol','med_trd','zero_vol','med_imb','p90_imb','med_tpk','p10_tpk','p90_tpk']:
    print("  %-12s median %10.3f   min %10.3f   max %10.3f"%(c, R[c].median(), R[c].min(), R[c].max()))
print()
print("TOTAL windows across 44 sessions: %d"%int(R.w30.sum()))
R.to_csv('/home/user/Claude-1/reports/rp010_stage0_window_inventory.csv',index=False)
