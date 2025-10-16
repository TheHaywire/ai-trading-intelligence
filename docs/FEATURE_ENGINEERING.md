## Quantitative Feature Engineering Guide

This guide explains practitioner-grade features used to generate signals in systematic trading. For each feature: what it measures, why it matters, how to compute, suggested parameters, and common pitfalls.

### How to use this guide
- Normalize inputs: use clean OHLCV, consistent timezone, no lookahead.
- Compute on rolling windows; align outputs to bar close to avoid leakage.
- Standardize features (z-scores/percentiles) before combining.
- Start simple: implement a small set per category and iterate.

## Momentum Features

### Price Rate of Change (ROC)
- What: Percent change over N periods: (price_t / price_{t-N}) − 1
- Why: Captures trend persistence; a building block for momentum.
- How: Use close prices; typical N: 5, 10, 20, 50.
- Pitfalls: Jumps around events; scale with volatility or use z-score.

### Return Autocorrelation
- What: Correlation between r_t and r_{t−lag} over a window.
- Why: Positive autocorrelation signals momentum; negative suggests mean reversion.
- How: Compute rolling Pearson corr; lags 1–5.
- Pitfalls: Non-stationarity; regime-dependent.

### MACD Signal Strength
- What: Absolute MACD histogram or signed histogram.
- Why: Combines two EMAs to measure momentum acceleration.
- How: EMA(12)−EMA(26); signal EMA(9); histogram = macd−signal.
- Pitfalls: Redundant with ROC if overused; smooth to reduce noise.

### Cross-Sectional Momentum
- What: Rank of a symbol’s recent return vs universe.
- Why: Winners tend to keep winning across assets (time-horizon dependent).
- How: Compute past 20–60 bar return; convert to percentile rank per scan.
- Pitfalls: Crowd risk; sector/FX base effects.

### Price Acceleration
- What: Second derivative of price (or momentum of momentum).
- Why: Detects momentum build-up or exhaustion.
- How: Difference of ROC or MACD histogram changes.
- Pitfalls: Highly noisy; smooth with longer windows.

## Mean Reversion Features

### Bollinger Band Percentile
- What: Where price sits within Bollinger bands (0–1 scale).
- Why: Mean-reversion pressure near extremes.
- How: bbp = (price−lower) / (upper−lower); window 20, k=2.
- Pitfalls: Bands widen in high vol; percentile stabilizes signal.

### Price Z-Score to Moving Average
- What: (price − MA) / rolling std.
- Why: Normalized deviation from equilibrium.
- How: Use SMA/EMA 20–50; std on same window.
- Pitfalls: Std instability in regime shifts.

### RSI Percentile
- What: RSI mapped to its historical percentile.
- Why: More robust than fixed 30/70 thresholds.
- How: RSI(14), then rolling percentile over 252 bars.
- Pitfalls: Short histories distort percentiles.

### OBV Divergence
- What: OBV trend vs price trend disagreement.
- Why: Volume failing to confirm price moves.
- How: Compare slopes over window; divergence = sign mismatch.
- Pitfalls: Requires clean volume; FX may use tick volume.

### Price vs VWAP Deviation
- What: Distance from VWAP (intraday or rolling).
- Why: Reversion toward fair value in liquid hours.
- How: Compute session VWAP or rolling VWAP; z-score deviation.
- Pitfalls: Session boundaries; low-liquidity hours.

## Volatility Features

### Historical Volatility (HV)
- What: Rolling std of returns.
- Why: Risk scaling; regime detection; filter for setups.
- How: log-returns std × √periods; windows 20–60.
- Pitfalls: Backward-looking; jumps miss real-time risk.

### Volatility of Volatility (VoV)
- What: Std of HV over a window.
- Why: Stability of the risk environment.
- How: Compute HV; then rolling std over 20–60.
- Pitfalls: Stacked estimation error; smooth carefully.

### Intraday Volatility Pattern
- What: Hour-of-day/weekday vol effects.
- Why: Timing entries to high-probability volatility windows.
- How: Average absolute returns by hour/day; normalize.
- Pitfalls: DST and session overlap handling.

### Volatility Regime Indicator
- What: Discrete state: low/medium/high vol.
- Why: Condition strategies (e.g., trend works in medium vol).
- How: Quantile bins of HV or Markov-switching on returns.
- Pitfalls: Regime transitions lag; avoid hard switches.

## Market Microstructure Features

### Bid-Ask Spread Dynamics
- What: Spread level and change.
- Why: Liquidity proxy; wide spreads degrade edges.
- How: Spread/price, rolling z-score.
- Pitfalls: Broker-dependent; off-hours spikes.

### Order Flow Imbalance (OFI)
- What: Buy vs sell pressure.
- Why: Predicts short-term direction.
- How: Tick aggregation: (buy_volume−sell_volume)/(total).
- Pitfalls: FX “volume” is proxy; use tick volume conservatively.

### VWAP Deviation
- What: Price distance to VWAP.
- Why: Mean-reversion intraday; magnet effect.
- How: Rolling/session VWAP; z-scored deviation.
- Pitfalls: Session resets; partial-day bias.

### Intraday Return Distribution Shape
- What: Skewness/kurtosis of intraday returns.
- Why: Tail risk and asymmetry awareness.
- How: Rolling higher moments over intraday bars.
- Pitfalls: Sample-size sensitivity; winsorize tails.

## Cross-Asset Features

### Correlation Breakdown
- What: Current correlation vs rolling baseline.
- Why: Regime shifts and pair opportunities.
- How: Rolling corr; z-score of corr change.
- Pitfalls: Non-stationary bases; window choice critical.

### Risk-On/Risk-Off Proxy
- What: Macro regime measure (e.g., equities↑, USD↓).
- Why: Conditions trend/mean-reversion edges.
- How: Composite of indices/FX/commodities; PCA or simple rules.
- Pitfalls: Overfitting composites; stale relationships.

### Carry Divergence (FX)
- What: Rate differential vs spot returns.
- Why: Carry alignment enhances trend edges.
- How: Use implied/benchmark rates; track sign agreement.
- Pitfalls: Data availability; proxies needed.

## Time-Series Structure Features

### Hurst Exponent
- What: Long-range dependence (H>0.5 trend; <0.5 mean-revert).
- Why: Match strategy to time-series character.
- How: R/S or DFA estimators; windows 256–1024 bars.
- Pitfalls: High variance; interpret in bands, not points.

### Fractal Dimension
- What: Roughness/complexity measure.
- Why: Filters for choppy vs smooth regimes.
- How: Katz/Higuchi estimators on price path.
- Pitfalls: Sensitive to sampling and noise.

### Seasonality Components
- What: Calendar effects (hour/day/month).
- Why: Timing and bias correction.
- How: Dummies or STL decomposition; encode as features.
- Pitfalls: Instability post-structural breaks.

## Economic/Calendar Features

### Event Proximity
- What: Time to/from major releases.
- Why: Volatility shock windows; trade suspend or fade logic.
- How: Scheduled calendar; minutes to event and since event.
- Pitfalls: Timezones; unexpected revisions.

### Volatility Risk Premium Around Events
- What: Expected vs realized vol delta near events.
- Why: Size down or switch strategy class.
- How: Pre/post window HV comparison; spread threshold.
- Pitfalls: Small samples per event type.

## Technical Ensemble Features

### MA Convergence/Divergence
- What: Distances between multiple MAs.
- Why: Trend maturity and compression signals.
- How: Normalize MA gaps by price or ATR.
- Pitfalls: Redundancy; control multicollinearity.

### Support/Resistance Strength
- What: Level importance from bounce/failure counts.
- Why: Context for entries/exits and TP placement.
- How: Detect swing points; score by touches/volume.
- Pitfalls: Curve-fitting specific levels.

### Ichimoku Positioning
- What: Price vs cloud, lagging span alignment.
- Why: Regime and momentum in one framework.
- How: Standard Ichimoku calculations; encode positions as features.
- Pitfalls: Parameter proliferation.

## Risk/Portfolio Features

### Drawdown Utilization/Acceleration
- What: Current DD and its rate of change.
- Why: De-risk when accelerating losses.
- How: Track equity peak-trough; derivative over time.
- Pitfalls: Equity calc timing; open PnL volatility.

### Correlation Clamp Signal
- What: Max correlation vs open book.
- Why: Prevents over-concentrated bet clusters.
- How: Rolling corr matrix; clamp if max|corr|>threshold.
- Pitfalls: Estimation noise; shrinkage helps.

## Machine Learning-Oriented Features

### PCA/ICA Factors
- What: Latent components explaining returns.
- Why: Reduce dimension; de-noise signals.
- How: PCA on standardized feature set; use top k loadings.
- Pitfalls: Component drift; re-train cadence.

### Clustering Distances
- What: Distance to nearest cluster centroid.
- Why: Regime or state identification.
- How: KMeans/GMM on features; online update or batch.
- Pitfalls: Non-stationarity; number of clusters.

### Text/Sentiment Features
- What: News or statement tone scores.
- Why: Event-driven bias and drift.
- How: Simple lexicon or API-based sentiment; map to symbol set.
- Pitfalls: Latency and mapping noise.

---

## Implementation Notes
- Windows/Timeframes: For FX/indices, compute features on M15/H1/H4/D1 as relevant; align entries on H1 with H4 filters.
- Normalization: Prefer rolling percentiles/z-scores to raw indicator levels.
- Feature Store: Cache rolling computations to avoid recomputation per symbol.
- Model Input: Start with 10–15 features (balanced across categories), then expand.
- Evaluation: Use walk-forward evaluation; monitor stability and turnover.


