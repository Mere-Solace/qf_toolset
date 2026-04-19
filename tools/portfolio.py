"""Portfolio: a weighted collection of Ticker / FI_ETF / Equity assets.

Build portfolios from symbol strings or Ticker objects, compare them
side-by-side, and decompose risk.  Designed to make it trivial to spin
up, tweak, and benchmark any set of allocations.

Quick start::

    from tools import Portfolio, FI_ETF

    core  = Portfolio({"AGG": 0.5, "TLT": 0.3, "IEF": 0.2}, name="Core Bond")
    barbell = Portfolio({"TLT": 0.5, "SHY": 0.5}, name="Barbell")
    bmark = Portfolio({"AGG": 1.0}, name="AGG Benchmark")

    # Stats table across all three
    Portfolio.compare(core, barbell, benchmark=bmark)

    # KRD profile (requires FI_ETF holdings or empirical regression)
    core.krd_profile("DGS2", "DGS5", "DGS10", "DGS30")
    core.krd_chart("DGS2", "DGS5", "DGS10", "DGS30").show()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from tools.series import Panel, TimeSeries
from tools.palette import Palette, NAVY, GOLD, COPPER

if TYPE_CHECKING:
    from tools.securities import Ticker
    from tools.charts import Chart
    from tools.excel import NotebookWorkbook


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class Portfolio:
    """Weighted collection of assets with portfolio-level analytics.

    Args:
        holdings: dict mapping symbol (str) or Ticker object → weight.
                  Weights are normalised to sum to 1 automatically.
        name:     display name for this portfolio (used in comparison tables).
        start:    start date passed to any Ticker objects created from strings.
        end:      end date passed to Ticker objects.
        asset_type: default class to use when a string symbol is given.
                    Defaults to Ticker; pass FI_ETF for bond portfolios.
    """

    def __init__(
        self,
        holdings: dict,
        name: str = "Portfolio",
        start=None,
        end=None,
        asset_type=None,
    ):
        from tools.securities import Ticker as _Ticker, FI_ETF

        self.name = name
        self._start = start
        self._end = end

        _default_cls = asset_type or _Ticker

        # Resolve string keys → Ticker objects
        resolved: dict[_Ticker, float] = {}
        for key, weight in holdings.items():
            if isinstance(key, str):
                obj = _default_cls(key, start=start, end=end)
            else:
                obj = key
            resolved[obj] = float(weight)

        # Normalise weights
        total = sum(resolved.values())
        if total <= 0:
            raise ValueError("Weights must sum to a positive number.")
        self._holdings: dict[Ticker, float] = {t: w / total for t, w in resolved.items()}

        # Caches
        self._constituent_returns_cache: Panel | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tickers(self) -> list[Ticker]:
        return list(self._holdings.keys())

    @property
    def weights(self) -> dict[str, float]:
        """Symbol → normalised weight."""
        return {t.symbol: w for t, w in self._holdings.items()}

    @property
    def symbols(self) -> list[str]:
        return list(self.weights.keys())

    @property
    def constituent_returns(self) -> Panel:
        """Aligned daily returns for each holding (lazy, cached)."""
        if self._constituent_returns_cache is None:
            frames = {t.symbol: t.returns.data[t.symbol] for t in self.tickers}
            df = pd.concat(frames, axis=1).dropna()
            self._constituent_returns_cache = Panel(df)
        return self._constituent_returns_cache

    @property
    def constituent_prices(self) -> Panel:
        """Aligned prices for each holding."""
        frames = {t.symbol: t.prices.data[t.symbol] for t in self.tickers}
        df = pd.concat(frames, axis=1).dropna()
        return Panel(df)

    @property
    def returns(self) -> pd.Series:
        """Daily portfolio returns (weighted sum of constituent returns)."""
        rets = self.constituent_returns.data
        w = np.array([self.weights[c] for c in rets.columns])
        port = (rets * w).sum(axis=1)
        return port.rename(self.name)

    @property
    def cumulative_returns(self) -> pd.Series:
        """Cumulative portfolio returns: (1+r).cumprod() - 1."""
        return ((1 + self.returns).cumprod() - 1).rename(self.name)

    # ------------------------------------------------------------------
    # Performance stats
    # ------------------------------------------------------------------

    def stats(self, rf: float = 0.0, periods: int = 252) -> pd.DataFrame:
        """Single-column performance stats for this portfolio.

        Rows: Ann Return, Ann Vol, Sharpe, Sortino, Max Drawdown, Calmar,
              Max DD Duration, Win Rate, Skew, Kurtosis.
        """
        r = self.returns.dropna()
        ann_ret = r.mean() * periods
        ann_vol = r.std() * np.sqrt(periods)
        sharpe  = (ann_ret - rf) / ann_vol if ann_vol else np.nan
        cum     = (1 + r).cumprod()
        max_dd  = (cum / cum.cummax() - 1).min()
        calmar  = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

        return pd.DataFrame(
            {
                self.name: {
                    "Ann Return":     ann_ret,
                    "Ann Vol":        ann_vol,
                    "Sharpe":         sharpe,
                    "Sortino":        self.sortino(rf=rf, periods=periods),
                    "Max Drawdown":   max_dd,
                    "Calmar":         calmar,
                    "Max DD Dur (d)": self.max_drawdown_duration(),
                    "Win Rate":       self.win_rate(),
                    "Skew":           r.skew(),
                    "Kurtosis":       r.kurt(),
                }
            }
        )

    def stats_vs(
        self, benchmark: Portfolio, rf: float = 0.0, periods: int = 252
    ) -> pd.DataFrame:
        """Benchmark-relative stats for this portfolio.

        Rows: Active Return, Tracking Error, Information Ratio, Beta, Alpha.
        """
        return pd.DataFrame(
            {
                self.name: {
                    "Active Return":      self.active_return(benchmark, periods),
                    "Tracking Error":     self.tracking_error(benchmark, periods),
                    "Information Ratio":  self.information_ratio(benchmark, periods),
                    "Beta":               self.beta_vs(benchmark),
                    "Alpha":              self.alpha_vs(benchmark, rf=rf, periods=periods),
                }
            }
        )

    # ------------------------------------------------------------------
    # Standalone performance metrics
    # ------------------------------------------------------------------

    def sortino(self, rf: float = 0.0, periods: int = 252) -> float:
        """Sortino ratio using only downside deviation below rf."""
        r = self.returns.dropna()
        ann_ret  = r.mean() * periods
        daily_rf = rf / periods
        downside = r[r < daily_rf].std() * np.sqrt(periods)
        return (ann_ret - rf) / downside if downside > 0 else np.nan

    def win_rate(self) -> float:
        """Fraction of trading days with a positive return."""
        r = self.returns.dropna()
        return float((r > 0).mean())

    def annual_returns(self) -> pd.Series:
        """Total return for each calendar year."""
        r = self.returns.dropna()
        return r.groupby(r.index.year).apply(lambda g: (1 + g).prod() - 1).rename(self.name)

    def max_drawdown_duration(self) -> int:
        """Longest drawdown in trading days (peak-to-recovery)."""
        cum = (1 + self.returns.dropna()).cumprod()
        in_dd = cum < cum.cummax()
        durations, current = [], 0
        for flag in in_dd:
            if flag:
                current += 1
            else:
                if current:
                    durations.append(current)
                current = 0
        if current:
            durations.append(current)
        return max(durations) if durations else 0

    # ------------------------------------------------------------------
    # Benchmark-relative metrics
    # ------------------------------------------------------------------

    def _active_returns(self, benchmark: Portfolio) -> pd.Series:
        """Daily active returns (self minus benchmark), aligned."""
        aligned = pd.concat([self.returns, benchmark.returns], axis=1).dropna()
        return aligned.iloc[:, 0] - aligned.iloc[:, 1]

    def tracking_error(self, benchmark: Portfolio, periods: int = 252) -> float:
        """Annualised tracking error vs benchmark."""
        active = self._active_returns(benchmark)
        return float(active.std() * np.sqrt(periods))

    def active_return(self, benchmark: Portfolio, periods: int = 252) -> float:
        """Annualised active return vs benchmark."""
        return float(self._active_returns(benchmark).mean() * periods)

    def information_ratio(self, benchmark: Portfolio, periods: int = 252) -> float:
        """Annualised active return / tracking error."""
        te = self.tracking_error(benchmark, periods)
        return self.active_return(benchmark, periods) / te if te > 0 else np.nan

    def beta_vs(self, benchmark: Portfolio) -> float:
        """Portfolio beta relative to benchmark returns."""
        aligned = pd.concat([self.returns, benchmark.returns], axis=1).dropna()
        cov = np.cov(aligned.values.T)
        return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else np.nan

    def alpha_vs(
        self, benchmark: Portfolio, rf: float = 0.0, periods: int = 252
    ) -> float:
        """Jensen alpha (annualised) vs benchmark."""
        beta    = self.beta_vs(benchmark)
        ann_p   = self.returns.dropna().mean() * periods
        ann_b   = benchmark.returns.dropna().mean() * periods
        return float(ann_p - (rf + beta * (ann_b - rf)))

    def drawdown(self) -> pd.Series:
        """Portfolio drawdown series: (cum / cummax) - 1."""
        cum = (1 + self.returns).cumprod()
        return (cum / cum.cummax() - 1).rename(self.name)

    def rolling_vol(self, window: int = 252, annualize: bool = True) -> pd.Series:
        """Rolling annualised volatility."""
        rv = self.returns.rolling(window).std()
        return (rv * np.sqrt(window) if annualize else rv).rename(self.name)

    def rolling_sharpe(
        self, window: int = 252, rf: float = 0.0, periods: int = 252
    ) -> pd.Series:
        """Rolling Sharpe ratio."""
        r = self.returns
        roll_ret = r.rolling(window).mean() * periods
        roll_vol = r.rolling(window).std() * np.sqrt(periods)
        return ((roll_ret - rf) / roll_vol).rename(self.name)

    # ------------------------------------------------------------------
    # Risk decomposition
    # ------------------------------------------------------------------

    def risk_contribution(self, annualize: bool = True, periods: int = 252) -> pd.Series:
        """Marginal contribution to portfolio volatility for each holding.

        Returns fractional contributions that sum to ~1.
        """
        rets = self.constituent_returns.data
        w = np.array([self.weights[c] for c in rets.columns])
        cov = rets.cov().values * (periods if annualize else 1)
        port_var = float(w @ cov @ w)
        marginal_contrib = cov @ w
        contrib = w * marginal_contrib / port_var
        return pd.Series(contrib, index=rets.columns, name=f"{self.name} risk contrib")

    def correlation_matrix(self) -> pd.DataFrame:
        """Correlation matrix of constituent returns."""
        return self.constituent_returns.correlation()

    def covariance_matrix(self, annualize: bool = True) -> pd.DataFrame:
        """Covariance matrix of constituent returns."""
        return self.constituent_returns.covariance(annualize=annualize)

    # ------------------------------------------------------------------
    # Key rate duration
    # ------------------------------------------------------------------

    def krd_profile(self, *fred_ids: str, start: str | None = None) -> pd.DataFrame:
        """Weighted key rate duration profile across rate tenors.

        For each constituent runs multivariate OLS (returns ~ Δy_tenor …)
        then weights by portfolio allocation.

        Args:
            *fred_ids: FRED IDs for each tenor, e.g. 'DGS2','DGS5','DGS10','DGS30'
            start:     optional date to restrict the regression window

        Returns:
            DataFrame with tenors as rows, columns = each symbol + 'Portfolio'.
            Bottom rows include r_squared and total_duration per holding.
        """
        from tools.securities import FI_ETF
        from tools.data import load_fred
        import statsmodels.api as sm

        rows: dict[str, dict] = {sid: {} for sid in fred_ids}
        r2_row: dict = {}
        total_row: dict = {}

        for ticker, w in self._holdings.items():
            sym = ticker.symbol

            # Prefer FI_ETF.key_rate_durations if available
            if isinstance(ticker, FI_ETF):
                krd = ticker.key_rate_durations(*fred_ids, start=start)
                for sid in fred_ids:
                    rows[sid][sym] = krd[sid]
                r2_row[sym] = krd.get("r_squared", np.nan)
                total_row[sym] = krd.get("total_duration", np.nan)
            else:
                # Empirical fallback for any Ticker
                rets = ticker.returns.data[sym]
                rate_changes = {}
                for sid in fred_ids:
                    s = load_fred(sid)
                    if start:
                        s = s[s.index >= pd.Timestamp(start)]
                    rate_changes[sid] = s.diff().dropna()

                aligned = pd.concat([rets, *rate_changes.values()], axis=1).dropna()
                aligned.columns = [sym] + list(fred_ids)
                if start:
                    aligned = aligned[aligned.index >= pd.Timestamp(start)]

                y_reg = aligned[sym]
                X_reg = sm.add_constant(aligned[list(fred_ids)])
                fit = sm.OLS(y_reg, X_reg).fit()

                for sid in fred_ids:
                    rows[sid][sym] = -fit.params[sid] * 100
                r2_row[sym] = fit.rsquared
                total_row[sym] = sum(-fit.params[sid] * 100 for sid in fred_ids)

        # Portfolio-weighted totals
        w_arr = self.weights
        for sid in fred_ids:
            rows[sid]["Portfolio"] = sum(
                rows[sid].get(sym, 0) * w_arr[sym] for sym in self.symbols
            )
        r2_row["Portfolio"] = np.nan
        total_row["Portfolio"] = sum(
            total_row.get(sym, 0) * w_arr[sym] for sym in self.symbols
        )

        df = pd.DataFrame(rows).T
        df.index.name = "Tenor"
        df.loc["R²"] = r2_row
        df.loc["Total Duration"] = total_row
        return df

    def krd_chart(self, *fred_ids: str, start: str | None = None) -> Chart:
        """Stacked bar chart of KRD contributions across tenors.

        Each colour = one holding; bar height = weighted KRD at that tenor.
        """
        from tools.charts import Chart

        profile = self.krd_profile(*fred_ids, start=start)
        tenor_rows = profile.loc[list(fred_ids), self.symbols]
        weights_arr = np.array([self.weights[s] for s in self.symbols])
        weighted = tenor_rows.multiply(weights_arr, axis=1)

        chart = Chart(figsize=(max(8, len(fred_ids) * 1.5), 5))
        ax = chart.ax()
        colors = Palette.navy(len(self.symbols))

        bottoms = np.zeros(len(fred_ids))
        x = np.arange(len(fred_ids))
        for i, sym in enumerate(self.symbols):
            vals = weighted[sym].values.astype(float)
            ax.bar(x, vals, bottom=bottoms, color=colors[i], label=sym, width=0.6)
            bottoms += vals

        ax.set_xticks(x)
        ax.set_xticklabels(fred_ids, rotation=30, ha="right")
        ax.set_ylabel("Key Rate Duration (years)")
        ax.set_title(f"{self.name} — KRD Profile")
        ax.legend(fontsize=9)
        ax.axhline(0, color="black", linewidth=0.5)

        return chart

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    @staticmethod
    def compare(
        *portfolios: Portfolio,
        benchmark: Portfolio | None = None,
        rf: float = 0.0,
    ) -> pd.DataFrame:
        """Side-by-side performance stats for multiple portfolios.

        When *benchmark* is provided, appends benchmark-relative rows
        (Active Return, Tracking Error, IR, Beta, Alpha) for each non-benchmark
        portfolio.  Benchmark column shows '—' for those rows.

        Returns:
            DataFrame with one column per portfolio, stat rows.
        """
        targets = list(portfolios)
        if benchmark and benchmark not in targets:
            targets.append(benchmark)

        frames = [p.stats(rf=rf) for p in targets]
        combined = pd.concat(frames, axis=1)

        if benchmark:
            rel_frames = []
            for p in targets:
                if p.name == benchmark.name:
                    placeholder = pd.DataFrame(
                        {p.name: {k: "—" for k in
                                  ["Active Return", "Tracking Error",
                                   "Information Ratio", "Beta", "Alpha"]}},
                    )
                else:
                    placeholder = p.stats_vs(benchmark, rf=rf)
                rel_frames.append(placeholder)
            rel = pd.concat(rel_frames, axis=1)
            combined = pd.concat([combined, rel])

        return combined.round(4)

    @staticmethod
    def plot_cumulative(
        *portfolios: Portfolio,
        benchmark: Portfolio | None = None,
        title: str = "Cumulative Returns",
        rebase: bool = True,
    ) -> Chart:
        """Cumulative return chart for multiple portfolios.

        Args:
            *portfolios: Portfolio instances to plot.
            benchmark:   optional benchmark drawn as a dashed line.
            rebase:      if True, rebase all series to 100 at first common date.
        """
        from tools.charts import Chart

        targets = list(portfolios)
        all_series = []
        for p in targets:
            all_series.append(p.cumulative_returns)

        aligned = pd.concat(all_series, axis=1).dropna()
        if rebase:
            aligned = (1 + aligned) * 100

        chart = Chart(figsize=(12, 5))
        ax = chart.ax()
        colors = Palette.series(len(targets))

        for i, col in enumerate(aligned.columns):
            is_bmark = benchmark and col == benchmark.name
            ax.plot(
                aligned.index,
                aligned[col],
                color=colors[i],
                linewidth=1.0 if not is_bmark else 0.8,
                linestyle="--" if is_bmark else "-",
                label=col,
            )

        ax.set_title(title, fontsize=12)
        ax.set_ylabel("Value (rebased to 100)" if rebase else "Cumulative Return")
        ax.legend(fontsize=9)
        return chart

    @staticmethod
    def plot_drawdowns(
        *portfolios: Portfolio,
        benchmark: Portfolio | None = None,
    ) -> Chart:
        """Drawdown chart for multiple portfolios."""
        from tools.charts import Chart

        targets = list(portfolios)
        if benchmark and benchmark not in targets:
            targets.append(benchmark)

        all_dd = {p.name: p.drawdown() for p in targets}
        aligned = pd.concat(all_dd, axis=1).dropna()

        chart = Chart(figsize=(12, 4))
        ax = chart.ax()
        colors = Palette.series(len(targets))

        for i, col in enumerate(aligned.columns):
            is_bmark = benchmark and col == benchmark.name
            ax.plot(
                aligned.index,
                aligned[col] * 100,
                color=colors[i],
                linewidth=0.9,
                linestyle="--" if is_bmark else "-",
                label=col,
            )

        ax.fill_between(aligned.index, aligned.min(axis=1) * 100, 0,
                        alpha=0.06, color=COPPER)
        ax.set_title("Drawdowns (%)", fontsize=12)
        ax.set_ylabel("%")
        ax.legend(fontsize=9)
        return chart

    @staticmethod
    def plot_rolling_sharpe(
        *portfolios: Portfolio,
        window: int = 252,
        rf: float = 0.0,
    ) -> Chart:
        """Rolling Sharpe ratio chart for multiple portfolios."""
        from tools.charts import Chart

        series = {p.name: p.rolling_sharpe(window=window, rf=rf) for p in portfolios}
        aligned = pd.concat(series, axis=1).dropna()

        chart = Chart(figsize=(12, 4))
        ax = chart.ax()
        colors = Palette.series(len(portfolios))
        for i, col in enumerate(aligned.columns):
            ax.plot(aligned.index, aligned[col], color=colors[i],
                    linewidth=0.9, label=col)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"Rolling Sharpe ({window}d)", fontsize=12)
        ax.legend(fontsize=9)
        return chart

    # ------------------------------------------------------------------
    # Rebalancing / construction
    # ------------------------------------------------------------------

    def rebalance(
        self, new_weights: dict[str | Ticker, float], name: str | None = None
    ) -> Portfolio:
        """Return a new Portfolio with updated weights (same tickers, new alloc).

        Symbols not in *new_weights* are dropped.  New symbols are added.
        """
        return Portfolio(
            new_weights,
            name=name or self.name,
            start=self._start,
            end=self._end,
        )

    def add(self, symbol: str | Ticker, weight: float, renorm: bool = True) -> Portfolio:
        """Return a new Portfolio with an additional holding.

        If *renorm* is True, all weights are re-normalised to sum to 1.
        """
        new = {**{t: w for t, w in self._holdings.items()}, symbol: weight}
        return Portfolio(new, name=self.name, start=self._start, end=self._end)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def to_excel(self, wb: NotebookWorkbook, prefix: str = "") -> None:
        """Write portfolio analytics to an Excel workbook.

        Writes sheets: Returns, Cumulative Returns, Drawdown, Stats,
        Weights, Risk Contribution, Correlation.
        """
        tag = f"{prefix}{self.name} " if prefix else f"{self.name} "

        # Constituent + portfolio returns
        rets_df = self.constituent_returns.data.copy()
        rets_df[self.name] = self.returns
        panel = Panel(rets_df)
        panel.to_excel(wb, f"{tag}Returns"[:31])

        # Cumulative
        cum = pd.DataFrame({
            col: (1 + rets_df[col]).cumprod() - 1
            for col in rets_df.columns
        })
        Panel(cum).to_excel(wb, f"{tag}Cumulative"[:31])

        # Drawdown
        dd_df = self.drawdown().to_frame()
        Panel(dd_df).to_excel(wb, f"{tag}Drawdown"[:31])

        # Stats
        wb.write(f"{tag}Stats"[:31],
                 self.stats().reset_index().rename(columns={"index": "Metric"}))

        # Weights
        wb.write(f"{tag}Weights"[:31],
                 pd.DataFrame(list(self.weights.items()), columns=["Symbol", "Weight"]))

        # Risk contribution
        wb.write(f"{tag}Risk Contrib"[:31],
                 self.risk_contribution().reset_index()
                 .rename(columns={"index": "Symbol", 0: "Risk Contrib"}))

        # Correlation
        wb.write(f"{tag}Correlation"[:31],
                 self.correlation_matrix().reset_index())

    def __repr__(self) -> str:
        w = ", ".join(f"{s}={v:.1%}" for s, v in self.weights.items())
        return f"Portfolio({self.name!r}: {w})"
