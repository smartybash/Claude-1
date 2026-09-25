"""RP-009 Table F inputs: strategy ARCHITECTURE only. No P&L is read or printed.

Entry window, median entry time, median risk, median holding time, target
multiple. Every number is a property of the setup, not of its outcome.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/Claude-1/scripts/orderflow')
import rp008_stage0 as A
import rp009_stage1 as S

lib = {}
lib.update(A.orb_and_pullback())
lib.update(A.ib_family_times())
lib.update(A.orb_fib_times())
cs,_ = A.compression_sets(); lib.update(cs)
lib.update(A.ib_midpoint_pullback())

# prior-session ATR in bps per day, and block-local, for converting risk
d = pd.read_parquet('/home/user/Claude-1/data/intraday_long/QQQ_1m.parquet',
                    columns=['timestamp','high','low','close'])
d['ts']=pd.to_datetime(d['timestamp']); d=d.sort_values('ts')
d['day']=d.ts.dt.normalize()
pc=d.groupby('day')['close'].shift()
tr=np.maximum(d.high-d.low, np.maximum((d.high-pc).abs(),(d.low-pc).abs()))
d['tr_bps']=1e4*tr/d.close
sa=d.groupby('day')['tr_bps'].mean().shift().rename('atr_bps')   # CAUSAL

TARGET={'ORB OR15 R3':3.0,'ORB OR15 R4':4.0,'ORB OR30 R3':3.0,'ORB OR30 R4':4.0,
        'pullback OR15 R3':3.0,'pullback OR30 R3':3.0,
        'IB 1R single':1.0,'IB 1R re-entry':1.0,
        'ORB-Fib cont ORB15 A':1.0,'ORB-Fib cont ORB30 A':1.0,
        'Compression D=10:00 flat':np.nan,'Compression D=10:30 flat':np.nan,
        'IB-mid pullback R2 (QQQ native)':1.5}
WINDOW={'ORB OR15 R3':'09:45 onward','ORB OR15 R4':'09:45 onward',
        'ORB OR30 R3':'10:00 onward','ORB OR30 R4':'10:00 onward',
        'pullback OR15 R3':'09:45 onward','pullback OR30 R3':'10:00 onward',
        'IB 1R single':'10:30 onward','IB 1R re-entry':'10:30 onward',
        'ORB-Fib cont ORB15 A':'09:45 onward','ORB-Fib cont ORB30 A':'10:00 onward',
        'Compression D=10:00 flat':'10:01 only','Compression D=10:30 flat':'10:31 only',
        'IB-mid pullback R2 (QQQ native)':'10:30-13:00'}

rows=[]
for name,T in lib.items():
    if 'm' not in T or T['m'].isna().all(): continue
    T=T.dropna(subset=['m']).copy()
    T['day']=pd.to_datetime(T['day']).dt.normalize()
    T['atr_bps']=T['day'].map(sa)
    rb = T['risk_bps'] if 'risk_bps' in T else pd.Series(np.nan, index=T.index)
    risk_atr = rb/T['atr_bps']
    # block of the median entry
    med_m=float(T['m'].median())
    blk=A.tod_of(med_m).split()[0]
    hold = T['j']-T['bar'] if ('j' in T and 'bar' in T) else pd.Series(np.nan,index=T.index)
    rows.append(dict(strategy=name, n=len(T), window=WINDOW.get(name,'?'),
        med_entry=med_m, blk=blk,
        med_risk_bps=float(rb.median()) if rb.notna().any() else np.nan,
        med_risk_atr=float(risk_atr.median()) if risk_atr.notna().any() else np.nan,
        med_cost_pct=float(T['cost_pct'].median()) if 'cost_pct' in T else
                     (float(T['cost_risk'].median()) if 'cost_risk' in T else np.nan),
        target=TARGET.get(name,np.nan),
        pct_open=100*float((T['m']<30).mean()), pct_morning=100*float(((T['m']>=30)&(T['m']<120)).mean()),
        pct_midday=100*float(((T['m']>=120)&(T['m']<270)).mean()),
        pct_close=100*float((T['m']>=270).mean())))
R=pd.DataFrame(rows).sort_values('n',ascending=False)
# NQ-point equivalent of the median risk, at the measured NQ price
R['risk_NQpt']=R.med_risk_bps*S.NQ_PX/1e4
R['cost_pct_NQ']=100*S.COST_BPS/R.med_risk_bps
R.to_csv('/home/user/Claude-1/reports/rp009_strategy_architecture.csv',index=False)
pd.set_option('display.width',250)
print(R[['strategy','n','window','med_entry','blk','med_risk_bps','med_risk_atr',
         'risk_NQpt','cost_pct_NQ','target','pct_open','pct_morning','pct_midday','pct_close']]
      .to_string(index=False,float_format='%.2f'))

# --- map-derived attainability. Uses ONLY the opportunity map's excursion
# distribution at the strategy's own median entry timestamp. No P&L.
E = pd.read_parquet('/home/user/Claude-1/reports/rp009_qqq_exc.parquet')
H = E[E.hz=='close'].copy()
def nearest_ts(m):
    return min(S.TS, key=lambda t: abs(t[1]-m))[0]
out=[]
for _,r in R.iterrows():
    ts = nearest_ts(r.med_entry)
    g = H[(H.ts==ts) & H.ok]
    ra = r.med_risk_atr
    tgt = r.target
    if not np.isfinite(ra):
        continue
    reach_stop = float((g.L_mae_a >= ra).mean())
    if np.isfinite(tgt):
        need = tgt*ra
        reach_tgt = float((g.L_mfe_a >= need).mean())
        neither = float(((g.L_mfe_a < need) & (g.L_mae_a < ra)).mean())
    else:
        need, reach_tgt, neither = np.nan, np.nan, np.nan
    out.append(dict(strategy=r.strategy, ts=ts, risk_atr=ra, target=tgt,
                    need_atr=need, mfe_close_med=float(g.L_mfe_a.median()),
                    pct_reach_target=100*reach_tgt if np.isfinite(tgt) else np.nan,
                    pct_reach_stop=100*reach_stop,
                    pct_neither=100*neither if np.isfinite(tgt) else np.nan,
                    cost_pct=r.cost_pct_NQ))
O=pd.DataFrame(out)
O.to_csv('/home/user/Claude-1/reports/rp009_strategy_attainability.csv',index=False)
print()
print('MAP-DERIVED ATTAINABILITY at each strategy median entry timestamp')
print(O.to_string(index=False,float_format='%.2f'))
