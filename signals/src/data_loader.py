"""Data contracts, cache lineage, and point-in-time alignment."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd

UNIVERSE = {
    'EMBASSY.NS': 'Embassy REIT', 'MINDSPACE.NS': 'Mindspace REIT',
    'BIRET.NS': 'Brookfield India REIT', 'NXST.NS': 'Nexus Select Trust',
    'DLF.NS': 'DLF', 'GODREJPROP.NS': 'Godrej Properties', 'PRESTIGE.NS': 'Prestige',
    'OBEROIRLTY.NS': 'Oberoi Realty', 'LODHA.NS': 'Lodha',
    'PHOENIXLTD.NS': 'Phoenix Mills', 'BRIGADE.NS': 'Brigade', 'SOBHA.NS': 'Sobha',
    '^CNXREALTY': 'Nifty Realty (benchmark only)',
}

def validate_panel(frame: pd.DataFrame, *, positive: bool = True) -> pd.DataFrame:
    """Reject duplicate/unsorted dates, infinities, and invalid prices. Keep NaNs.

    Missing prices are never backfilled or interpolated; pre-listing rows remain
    missing. Each pair must have contiguous observed rows in its training window.
    """
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError('DatetimeIndex required')
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Dates must be unique and sorted')
    if frame.columns.has_duplicates or frame.empty:
        raise ValueError('Nonempty panel with unique symbols required')
    a = frame.to_numpy(dtype=float)
    if np.isinf(a).any() or (positive and (a[np.isfinite(a)] <= 0).any()):
        raise ValueError('Invalid numeric observations')
    return frame.astype(float)

def download_prices(cache: Path, start: str, end: str,
                    tickers: list[str] | None = None, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download adjusted prices plus unadjusted traded value for ADV limits.

    Yahoo adjusted prices are a vendor total-return proxy, not audited REIT
    distribution accounting. Raw data stay local; license terms govern reuse.
    The cache key includes the request. Never silently replace failed data.
    """
    import yfinance as yf
    tickers = tickers or list(UNIVERSE)
    key = hashlib.sha256(json.dumps([start, end, tickers]).encode()).hexdigest()[:16]
    cache.mkdir(parents=True, exist_ok=True)
    price_file, value_file = cache/f'{key}_prices.csv', cache/f'{key}_value.csv'
    if price_file.exists() and value_file.exists() and not refresh:
        return (validate_panel(pd.read_csv(price_file, index_col=0, parse_dates=True)),
                validate_panel(pd.read_csv(value_file, index_col=0, parse_dates=True), positive=False))
    prices, values, errors = {}, {}, {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=True, raise_errors=True)
            if df.empty or 'Adj Close' not in df: raise ValueError('No adjusted close')
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            prices[ticker] = df['Adj Close']
            values[ticker] = df['Close'] * df['Volume']
        except Exception as exc:
            errors[ticker] = str(exc)
    if len(prices) < 2:
        raise RuntimeError(f'Insufficient downloaded series; no synthetic fallback: {errors}')
    p = validate_panel(pd.DataFrame(prices).sort_index())
    v = pd.DataFrame(values).reindex(p.index)
    p.to_csv(price_file); v.to_csv(value_file)
    meta = dict(provider='Yahoo via yfinance', retrieved_utc=datetime.now(timezone.utc).isoformat(),
                start=start, end_exclusive=end, requested=tickers, errors=errors,
                price_sha256=hashlib.sha256(price_file.read_bytes()).hexdigest(),
                value_sha256=hashlib.sha256(value_file.read_bytes()).hexdigest())
    (cache/f'{key}_manifest.json').write_text(json.dumps(meta, indent=2))
    return p, v

def align_rates(path: Path, dates: pd.DatetimeIndex, max_age_days: int = 7) -> pd.Series:
    """RBI/CCIL CSV: observation_date, available_date, yield_pct.

    Join by publication availability, not observation date. Conservative lagging
    is a documented assumption when actual release timestamps are unavailable.
    Stale rates are missing, causing the rate-dependent strategy to stay flat.
    """
    r = pd.read_csv(path, parse_dates=['observation_date', 'available_date'])
    if r['available_date'].duplicated().any(): raise ValueError('Duplicate publication date')
    if (r.available_date < r.observation_date).any(): raise ValueError('Publication precedes observation')
    if not np.isfinite(r.yield_pct).all() or not r.yield_pct.between(-5, 30).all():
        raise ValueError('yield_pct must be finite percentage points, e.g. 7.2')
    left = pd.DataFrame({'date': dates})
    merged = pd.merge_asof(left, r.sort_values('available_date'), left_on='date',
                           right_on='available_date', direction='backward')
    age = (merged.date - merged.observation_date).dt.days
    return pd.Series((merged.yield_pct/100).where(age <= max_age_days).to_numpy(), index=dates, name='gsec_yield')

def trailing_distribution_yield(events: pd.DataFrame, raw_prices: pd.DataFrame) -> pd.DataFrame:
    """Sum distributions whose ex-date AND known date have occurred in last year.

    Events: ticker, ex_date, available_date, cash_per_unit. Raw prices must be on
    the same unit basis as distributions. Never divide distributions by adjusted
    prices. A missing distribution history must not be interpreted as zero yield.
    """
    required = {'ticker', 'ex_date', 'available_date', 'cash_per_unit'}
    if not required.issubset(events): raise ValueError('Distribution schema incomplete')
    e = events.copy()
    for c in ['ex_date', 'available_date']: e[c] = pd.to_datetime(e[c])
    if not np.isfinite(e.cash_per_unit).all() or (e.cash_per_unit < 0).any():
        raise ValueError('Invalid distribution cash')
    out = pd.DataFrame(np.nan, index=raw_prices.index, columns=raw_prices.columns)
    for ticker in raw_prices:
        ev = e[e.ticker == ticker]
        if ev.empty: continue
        for date in raw_prices.index:
            # Require a full 365-day observed event history before emitting yield.
            if date < ev.ex_date.min() + pd.Timedelta(days=365): continue
            known = ev[(ev.ex_date <= date) & (ev.available_date <= date) &
                       (ev.ex_date > date-pd.Timedelta(days=365))]
            out.loc[date, ticker] = known.cash_per_unit.sum()/raw_prices.loc[date,ticker]
    return out

def synthetic_fixture(n: int = 1008, seed: int = 336) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Named SYNTH series; never passed off as Indian market observations."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2022-01-03', periods=n)
    common = np.cumsum(rng.normal(.00015, .009, n)) + 5.6
    residual = np.zeros(n)
    for t in range(1,n): residual[t] = .88*residual[t-1]+rng.normal(0,.007)
    p = pd.DataFrame({'SYNTH_A':np.exp(common+residual),
                      'SYNTH_B':np.exp(common),
                      'SYNTH_C':np.exp(5.5+np.cumsum(rng.normal(0,.012,n)))}, index=dates)
    v = pd.DataFrame(8e7, index=dates, columns=p.columns)
    changes = np.where((np.arange(n)//100)%2==0,-.00004,.00004)+rng.normal(0,.00008,n)
    rates = pd.Series(.07+np.cumsum(changes), index=dates)
    yields = pd.DataFrame(.075+np.cumsum(rng.normal(0,.0001,(n,3)),axis=0),index=dates,columns=p.columns)
    return p,v,rates,yields
