# Sector Rotation Strategy Backtest Results

**Generated:** 2026-03-14  
**Period:** 2012-01-01 to 2025-12-31  
**Universe:** XLK, XLF, XLV, XLE, XBI, SMH, EEM, FXI, EWJ, GLD, TLT, SLV, USO, HYG  
**Risk-Free Rate:** 2.02% (avg FEDFUNDS)  
**Commission:** 0.1% per side  
**Lookback:** 3 months (63 trading days)  
**Rebalance:** Monthly  

## Strategy Overview

Monthly sector rotation strategy. Ranks sector ETFs by trailing 3-month return,
buys equal-weight top N sectors, rebalances monthly.

**Base variants:** Top 2, 3, 4, 5 sectors
**VIX filter:** VIX > 25 → 50% cash allocation; VIX > 35 → 100% cash
**Yield curve filter:** T10Y2Y < 0 (inverted) → hold defensive (GLD, TLT, SHY)

## Results Table

| Strategy                 | Filter   | Total Return   | Ann. Return   | Max Drawdown   |   Sharpe Ratio |   Calmar Ratio | Win Rate   | Best Year   | Worst Year   |   N Trades | Turnover   |
|:-------------------------|:---------|:---------------|:--------------|:---------------|---------------:|---------------:|:-----------|:------------|:-------------|-----------:|:-----------|
| SR Top2                  | None     | 136.3%         | 6.4%          | -46.2%         |           0.22 |           0.14 | 56.3%      | 79.3%       | -30.3%       |        352 | 53.0%      |
| SR Top3                  | None     | 200.8%         | 8.2%          | -36.7%         |           0.36 |           0.22 | 55.1%      | 60.5%       | -18.8%       |        467 | 46.9%      |
| SR Top4                  | None     | 233.1%         | 9.0%          | -31.2%         |           0.46 |           0.29 | 56.9%      | 51.5%       | -19.4%       |        536 | 40.4%      |
| SR Top5                  | None     | 244.6%         | 9.3%          | -29.2%         |           0.48 |           0.32 | 62.3%      | 44.5%       | -18.3%       |        627 | 37.8%      |
| SR Top3 +VIX             | VIX      | 133.3%         | 6.3%          | -36.3%         |           0.24 |           0.17 | 53.9%      | 60.5%       | -18.3%       |        451 | 48.3%      |
| SR Top4 +VIX             | VIX      | 181.7%         | 7.7%          | -30.7%         |           0.36 |           0.25 | 56.3%      | 51.5%       | -18.8%       |        528 | 43.0%      |
| SR Top5 +VIX             | VIX      | 164.4%         | 7.2%          | -28.0%         |           0.33 |           0.26 | 61.7%      | 44.5%       | -16.9%       |        617 | 40.8%      |
| SR Top3 +YC              | YC       | 139.8%         | 6.5%          | -36.7%         |           0.28 |           0.18 | 53.9%      | 60.5%       | -18.8%       |        409 | 41.1%      |
| SR Top3 +VIX+YC          | VIX+YC   | 80.7%          | 4.3%          | -36.3%         |           0.14 |           0.12 | 52.7%      | 60.5%       | -18.3%       |        395 | 42.5%      |
| SPY Buy & Hold           | None     | 564.9%         | 14.6%         | -23.9%         |           0.83 |           0.61 | 70.7%      | 32.3%       | -18.2%       |          0 | 0.0%       |
| Equal-Weight All Sectors | None     | 247.2%         | 9.4%          | -20.8%         |           0.57 |           0.45 | 65.3%      | 29.9%       | -8.4%        |          0 | ~100%      |

## Annual Returns by Variant

|   Year | SR Top2   | SR Top3   | SR Top4   | SR Top5   | SR Top3 +VIX   | SR Top4 +VIX   | SR Top5 +VIX   | SR Top3 +YC   | SR Top3 +VIX+YC   | SPY Buy & Hold   | EW Sectors   |
|-------:|:----------|:----------|:----------|:----------|:---------------|:---------------|:---------------|:--------------|:------------------|:-----------------|:-------------|
|   2012 | 0.3%      | 3.3%      | 4.4%      | 2.4%      | 3.3%           | 4.4%           | 2.4%           | 3.3%          | 3.3%              | 10.8%            | 5.0%         |
|   2013 | -3.0%     | -1.2%     | 5.9%      | 12.2%     | -1.2%          | 5.9%           | 12.2%          | -1.2%         | -1.2%             | 32.3%            | 9.9%         |
|   2014 | 4.1%      | 11.5%     | 10.3%     | 11.5%     | 11.5%          | 10.3%          | 11.5%          | 11.5%         | 11.5%             | 13.5%            | 5.3%         |
|   2015 | -30.3%    | -18.8%    | -19.4%    | -18.3%    | -18.3%         | -18.8%         | -16.9%         | -18.8%        | -18.3%            | 1.2%             | -6.6%        |
|   2016 | -8.3%     | -10.6%    | -6.4%     | -5.5%     | -10.6%         | -6.4%          | -5.5%          | -10.6%        | -10.6%            | 12.0%            | 11.3%        |
|   2017 | 2.4%      | 8.8%      | 17.4%     | 16.5%     | 8.8%           | 17.4%          | 16.5%          | 8.8%          | 8.8%              | 21.7%            | 20.8%        |
|   2018 | -0.2%     | -1.0%     | -3.4%     | -8.0%     | -1.0%          | -3.4%          | -8.0%          | -1.0%         | -1.0%             | -4.6%            | -8.4%        |
|   2019 | 11.8%     | 15.3%     | 18.7%     | 20.7%     | 16.4%          | 19.0%          | 19.3%          | 15.3%         | 16.4%             | 31.2%            | 26.0%        |
|   2020 | 10.2%     | 21.6%     | 27.7%     | 31.0%     | -6.1%          | -2.7%          | -7.0%          | 21.6%         | -6.1%             | 18.3%            | 13.0%        |
|   2021 | 18.6%     | 18.6%     | 16.6%     | 23.4%     | 15.4%          | 18.6%          | 24.0%          | 18.6%         | 15.4%             | 28.7%            | 12.4%        |
|   2022 | 15.5%     | 4.8%      | 2.5%      | -2.8%     | 6.5%           | 10.8%          | 4.0%           | -7.1%         | -8.2%             | -18.2%           | -8.1%        |
|   2023 | 8.7%      | 9.3%      | 2.9%      | 7.4%      | 9.3%           | 2.9%           | 7.4%           | 6.9%          | 6.9%              | 26.2%            | 13.1%        |
|   2024 | 8.6%      | 10.6%     | 12.8%     | 10.5%     | 10.6%          | 12.8%          | 10.5%          | 1.6%          | 1.6%              | 24.9%            | 15.0%        |
|   2025 | 79.3%     | 60.5%     | 51.5%     | 44.5%     | 60.5%          | 51.5%          | 44.5%          | 60.5%         | 60.5%             | 17.7%            | 29.9%        |

## Filter Analysis

### VIX Filter
The VIX filter reduces exposure during high-volatility regimes:
- VIX > 35: Move to 100% cash (avoids crash-period losses)
- VIX > 25: Move to 50% cash (partial protection)

### Yield Curve Filter
When the yield curve inverts (T10Y2Y < 0), the strategy switches to
defensive assets (GLD, TLT, SHY) to preserve capital.
Historically, inversions precede recessions by 6–18 months.

## Key Findings

- **Best Risk-Adjusted (Sharpe):** SPY Buy & Hold (0.83)
- **Best Raw Return:** SPY Buy & Hold (14.6% annualized)
- **Smallest Max Drawdown:** Equal-Weight All Sectors (-20.8%)

### Observations
- Sector rotation exploits relative strength across economic sectors.
- Defensive filters (VIX, yield curve) reduce tail risk at the cost of some upside.
- The combined VIX+YC filter may over-protect during choppy but non-crash markets.
- Technology (XLK, SMH) and healthcare (XLV) tend to rank highly in bull markets.
- Commodities (USO, SLV) and EM (EEM, FXI) add diversification but increase vol.
