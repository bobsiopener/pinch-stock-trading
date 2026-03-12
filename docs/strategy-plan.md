# Pinch Stock Trading — Master Strategy Plan

> *"Rule of Acquisition #22: A wise man can hear profit in the wind."*

## Overview

This document is the master strategy plan for the Pinch stock trading platform. It defines the strategy families under research, the evaluation criteria, and the path to deployment.

## Strategy Universe

### Candidates Under Research

| # | Strategy | Risk Level | Expected Sharpe | Rebalance |
|---|----------|------------|-----------------|-----------|
| 1 | Growth/Momentum | Medium-High | 0.6–1.0 | Monthly |
| 2 | Value Investing | Medium | 0.4–0.8 | Quarterly |
| 3 | Dividend/Income | Low-Medium | 0.5–0.9 | Quarterly |
| 4 | Sector Rotation | Medium | 0.5–0.8 | Monthly |
| 5 | Mean Reversion | Medium | 0.4–0.7 | Weekly |
| 6 | Factor Model | Medium | 0.6–0.9 | Monthly |
| 7 | Options Overlay | Low | Income+ | Ongoing |
| 8 | Macro/Tactical | Low-Medium | 0.4–0.7 | Monthly |

## Decision Framework

A strategy advances to backtesting if:
- [ ] Documented academic or practitioner basis
- [ ] Clear entry/exit rules
- [ ] Applicable to available data (38 symbols, 2010–2026)
- [ ] Expected Sharpe ratio > 0.4

A strategy advances to paper trading if:
- [ ] Backtested Sharpe > 0.5
- [ ] Max drawdown < 25%
- [ ] Outperforms SPY on risk-adjusted basis
- [ ] Walk-forward validation passes

## Portfolio Construction

**Starting Capital:** $500,000
**Benchmark:** 70% SPY / 30% QQQ
**Target:** Beat benchmark by 2%+ annually with lower drawdown

### Allocation Tiers (target)
- Core (60–70%): Best 1–2 strategies
- Satellite (20–30%): Complementary strategies
- Cash Reserve (10–15%): Minimum always held

## Risk Framework

- Max single position: 10% of portfolio
- Max sector concentration: 30%
- Stop loss: Strategy-specific (see individual research docs)
- Portfolio stop: -15% drawdown triggers review
- Kill switch: -20% drawdown halts all new positions
- Cross-asset: Monitor correlation with crypto portfolio

## Timeline

| Phase | Duration | Milestone |
|-------|----------|-----------|
| Phase 1 | 4–6 weeks | All 8 strategies researched |
| Phase 2 | 4–6 weeks | All strategies backtested |
| Phase 3 | 2–3 weeks | Portfolio system built |
| Phase 4 | 4–8 weeks | Paper trading complete |
| Phase 5 | Ongoing | Signal enhancement |
| Phase 6 | TBD | Go live (broker selected) |

## Data Assets

| Dataset | Location | Coverage |
|---------|----------|----------|
| Daily OHLCV (38 symbols) | pinch_market.db / prices | 2010–present |
| FRED economic data | pinch_market.db / fred_data | 1990–present |
| VIX | pinch_market.db | 1990–present |
| Options chains | pinch_market.db / options | Accumulating |
| CBOE put/call ratio | pinch_market.db | Recent |

*Last updated: auto-generated during repo initialization*
