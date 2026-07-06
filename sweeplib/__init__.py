"""Shared machinery for the same-day liquidity sweep/run program.

data.py    Parquet cache building/loading (IBKR columnar JSON -> parquet)
levels.py  pre-session level sets: PDH/PDL, PWH/PWL, equal-H/L pools, round numbers
engine.py  the causal touch -> confirmation-window -> sweep/run classifier,
           used bar-by-bar by BOTH the backtest and the live screener
"""
