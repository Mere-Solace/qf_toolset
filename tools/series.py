"""Data containers for financial time series analysis.

TimeSeries  — single date-indexed series with financial methods
Panel       — multi-column DataFrame wrapper with stats, PCA, cointegration

Both expose a `.data` attribute for raw pandas access and return their own
type from transformation methods so calls can be chained.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from tools.charts import Chart
    from tools.excel import NotebookWorkbook


# ---------------------------------------------------------------------------
# TimeSeries
# ---------------------------------------------------------------------------

class TimeSeries:
    """Single date-indexed Series with financial helper methods."""

    def __init__(self, data: pd.Series, name: str | None = None):
        if not isinstance(data.index, pd.DatetimeIndex):
            data = data.copy()
            data.index = pd.to_datetime(data.index)
        self.data = data.rename(name) if name else data

    @property
    def name(self) -> str | None:
        return self.data.name

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"TimeSeries({self.name!r}, {self.data.index[0].date()} – {self.data.index[-1].date()}, n={len(self)})"

    # ------------------------------------------------------------------
    # Transformations — return new TimeSeries
    # ------------------------------------------------------------------

    def returns(self, log: bool = False) -> TimeSeries:
        """Period-over-period returns (arithmetic or log)."""
        if log:
            r = np.log(self.data).diff().dropna()
        else:
            r = self.data.pct_change().dropna()
        label = f"{self.name}_log_ret" if log else f"{self.name}_ret"
        return TimeSeries(r, name=label)

    def rolling_vol(self, window: int = 252, annualize: bool = True) -> TimeSeries:
        """Rolling standard deviation, optionally annualised."""
        rv = self.data.rolling(window).std()
        if annualize:
            rv = rv * np.sqrt(window)
        return TimeSeries(rv, name=f"{self.name}_vol{window}")

    def zscore(self, window: int = 252 * 5) -> TimeSeries:
        """Rolling z-score over *window* periods."""
        mu = self.data.rolling(window).mean()
        sigma = self.data.rolling(window).std()
        z = (self.data - mu) / sigma
        return TimeSeries(z, name=f"{self.name}_zscore")

    def resample(self, freq: str = "ME", agg: str = "last") -> TimeSeries:
        """Resample to a lower frequency (e.g. 'ME', 'QE', 'YE')."""
        rs = getattr(self.data.resample(freq), agg)()
        return TimeSeries(rs, name=self.name)

    def dropna(self) -> TimeSeries:
        return TimeSeries(self.data.dropna(), name=self.name)

    def last(self, offset: str) -> TimeSeries:
        """Return the trailing slice defined by *offset* (e.g. '252B', '1Y', '6ME').

        Replacement for the deprecated pandas Series.last() method.
        """
        cutoff = self.data.index[-1] - pd.tseries.frequencies.to_offset(offset)
        return TimeSeries(self.data[self.data.index > cutoff], name=self.name)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def cointegrate_with(
        self, other: TimeSeries, significance: float = 0.05
    ) -> dict:
        """Engle-Granger cointegration test vs *other*.

        Returns dict with keys: stat, p_value, cointegrated, critical_values.
        """
        from statsmodels.tsa.stattools import coint

        aligned = pd.concat([self.data, other.data], axis=1).dropna()
        if aligned.shape[0] < 30:
            raise ValueError("Need at least 30 aligned observations for cointegration test.")
        stat, p_value, crit = coint(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return {
            "stat": stat,
            "p_value": p_value,
            "cointegrated": p_value < significance,
            "critical_values": {"1%": crit[0], "5%": crit[1], "10%": crit[2]},
        }

    def correlation_with(
        self, other: TimeSeries, method: str = "pearson"
    ) -> float:
        """Correlation coefficient vs *other* over aligned dates."""
        aligned = pd.concat([self.data, other.data], axis=1).dropna()
        return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method=method))

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def plot(self, title: str | None = None, **kwargs) -> Chart:
        """Return a Chart with this series plotted as a time series."""
        from tools.charts import Chart

        chart = Chart()
        chart.time_series(self, title=title or self.name, **kwargs)
        return chart

    def to_excel(self, wb: NotebookWorkbook, sheet_name: str) -> None:
        """Write this series to an Excel sheet in *wb*."""
        df = self.data.reset_index()
        df.columns = ["date", self.name or "value"]
        wb.write(sheet_name, df)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class Panel:
    """Multi-column date-indexed DataFrame with financial methods.

    Transformations return a new Panel; statistical analyses return
    DataFrames or plain Python objects.  Access raw pandas via `.data`.
    """

    def __init__(self, data: pd.DataFrame):
        if not isinstance(data.index, pd.DatetimeIndex):
            data = data.copy()
            data.index = pd.to_datetime(data.index)
        self.data = data

    # ------------------------------------------------------------------
    # Pandas delegation helpers
    # ------------------------------------------------------------------

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.data.index

    @property
    def columns(self) -> pd.Index:
        return self.data.columns

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        cols = list(self.data.columns)
        date_range = f"{self.data.index[0].date()} – {self.data.index[-1].date()}"
        return f"Panel({cols}, {date_range}, n={len(self)})"

    def __getitem__(self, key):
        result = self.data[key]
        if isinstance(result, pd.DataFrame):
            return Panel(result)
        return TimeSeries(result, name=str(key))

    def dropna(self, how: str = "any") -> Panel:
        return Panel(self.data.dropna(how=how))

    def ffill(self) -> Panel:
        return Panel(self.data.ffill())

    # ------------------------------------------------------------------
    # Transformations — return Panel
    # ------------------------------------------------------------------

    def pct_change(self, log: bool = False) -> Panel:
        """Period-over-period returns.  Drops leading NaN row."""
        if log:
            result = np.log(self.data).diff().dropna()
        else:
            result = self.data.pct_change().dropna()
        return Panel(result)

    def rolling_vol(self, window: int = 252, annualize: bool = True) -> Panel:
        """Rolling standard deviation for each column."""
        rv = self.data.rolling(window).std()
        if annualize:
            rv = rv * np.sqrt(window)
        return Panel(rv)

    def zscore(self, window: int = 252 * 5) -> Panel:
        """Rolling z-score for each column."""
        mu = self.data.rolling(window).mean()
        sigma = self.data.rolling(window).std()
        return Panel((self.data - mu) / sigma)

    def drawdown(self) -> Panel:
        """Drawdown series: (price / cumulative max) - 1."""
        dd = self.data / self.data.cummax() - 1
        return Panel(dd)

    def resample(self, freq: str = "ME", agg: str = "last") -> Panel:
        """Resample to lower frequency.  agg: 'last', 'mean', 'sum', etc."""
        rs = getattr(self.data.resample(freq), agg)()
        return Panel(rs)

    def cumulative_returns(self) -> Panel:
        """Cumulative returns from first period: (1 + r).cumprod() - 1."""
        return Panel((1 + self.data).cumprod() - 1)

    def rebase(self, base: float = 100.0) -> Panel:
        """Rebase price levels so the first row = *base*."""
        return Panel(self.data / self.data.iloc[0] * base)

    def align_with(self, *others: Panel, method: str = "ffill") -> Panel:
        """Outer-join this Panel with one or more others and forward-fill."""
        frames = [self.data] + [o.data for o in others]
        combined = pd.concat(frames, axis=1).sort_index()
        if method:
            combined = combined.ffill()
        return Panel(combined)

    # ------------------------------------------------------------------
    # Statistical analysis — return DataFrames / scalars / tuples
    # ------------------------------------------------------------------

    def correlation(self, method: str = "pearson") -> pd.DataFrame:
        """Pairwise correlation matrix."""
        return self.data.corr(method=method)

    def covariance(self, annualize: bool = True, periods: int = 252) -> pd.DataFrame:
        """Covariance matrix, optionally annualised."""
        cov = self.data.cov()
        return cov * periods if annualize else cov

    def variance(self, annualize: bool = True, periods: int = 252) -> pd.Series:
        """Per-column variance, optionally annualised."""
        v = self.data.var()
        return v * periods if annualize else v

    def sortino(self, rf: float = 0.0, periods: int = 252) -> pd.Series:
        """Sortino ratio per column using downside deviation only."""
        daily_rf = rf / periods
        ann_ret  = self.data.mean() * periods
        downside = self.data[self.data < daily_rf].std() * np.sqrt(periods)
        return (ann_ret - rf) / downside.replace(0, np.nan)

    def win_rate(self) -> pd.Series:
        """Fraction of periods with positive return, per column."""
        return (self.data > 0).mean()

    def annual_returns(self) -> pd.DataFrame:
        """Total return for each calendar year, per column.

        Returns a plain DataFrame indexed by integer year (not a Panel,
        since the index is years rather than dates).
        """
        df = self.data.groupby(self.data.index.year).apply(
            lambda g: (1 + g).prod() - 1
        )
        df.index.name = "Year"
        return df

    def stats(self, rf: float = 0.0, periods: int = 252) -> pd.DataFrame:
        """Summary performance statistics for each column.

        Returns a DataFrame with columns as assets and rows:
        Ann Return, Ann Vol, Sharpe, Sortino, Max Drawdown, Calmar,
        Win Rate, Skew, Kurtosis.
        """
        rets = self.data
        ann_ret = rets.mean() * periods
        ann_vol = rets.std() * np.sqrt(periods)
        sharpe  = (ann_ret - rf) / ann_vol
        cum     = (1 + rets).cumprod()
        max_dd  = (cum / cum.cummax() - 1).min()
        calmar  = ann_ret / max_dd.abs().replace(0, np.nan)
        skew    = rets.skew()
        kurt    = rets.kurt()

        return pd.DataFrame(
            {
                "Ann Return":   ann_ret,
                "Ann Vol":      ann_vol,
                "Sharpe":       sharpe,
                "Sortino":      self.sortino(rf=rf, periods=periods),
                "Max Drawdown": max_dd,
                "Calmar":       calmar,
                "Win Rate":     self.win_rate(),
                "Skew":         skew,
                "Kurtosis":     kurt,
            }
        ).T

    def pca(
        self, n_components: int = 3
    ) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        """PCA on this Panel.

        Returns:
            loadings   — (n_components × n_cols) DataFrame of eigenvectors
            scores     — (n_rows × n_components) DataFrame of factor scores
            explained  — 1-D array of explained variance ratios
        """
        clean = self.data.dropna()
        centered = clean.values - clean.values.mean(axis=0)
        scaled = centered / (clean.values.std(axis=0) + 1e-12)
        U, s, Vt = np.linalg.svd(scaled - scaled.mean(axis=0), full_matrices=False)

        var_per_pc = s ** 2 / (len(clean) - 1)
        explained = var_per_pc / var_per_pc.sum()

        n = min(n_components, len(s))
        loadings = pd.DataFrame(
            Vt[:n],
            index=[f"PC{i+1}" for i in range(n)],
            columns=self.data.columns,
        )
        scores = pd.DataFrame(
            (scaled - scaled.mean(axis=0)) @ Vt[:n].T,
            index=clean.index,
            columns=[f"PC{i+1}" for i in range(n)],
        )

        # Sign convention: largest absolute loading positive
        for i in range(n):
            if loadings.iloc[i].abs().idxmax() and loadings.iloc[i][loadings.iloc[i].abs().idxmax()] < 0:
                loadings.iloc[i] *= -1
                scores.iloc[:, i] *= -1

        return loadings, scores, explained[:n]

    def cointegration(self, significance: float = 0.05) -> pd.DataFrame:
        """Pairwise Engle-Granger cointegration p-values.

        Returns a DataFrame of p-values; values below *significance* indicate
        a cointegrated pair.
        """
        from statsmodels.tsa.stattools import coint

        cols = list(self.data.columns)
        n = len(cols)
        p_matrix = pd.DataFrame(np.nan, index=cols, columns=cols)

        clean = self.data.dropna()
        for i, c1 in enumerate(cols):
            for j, c2 in enumerate(cols):
                if i == j:
                    continue
                if not np.isnan(p_matrix.loc[c2, c1]):
                    p_matrix.loc[c1, c2] = p_matrix.loc[c2, c1]
                    continue
                try:
                    _, p, _ = coint(clean[c1], clean[c2])
                    p_matrix.loc[c1, c2] = p
                except Exception:
                    pass

        return p_matrix

    def rolling_correlation(
        self, window: int = 252
    ) -> dict[tuple[str, str], pd.Series]:
        """Rolling pairwise correlations for all column pairs."""
        cols = list(self.data.columns)
        result: dict[tuple[str, str], pd.Series] = {}
        for i, c1 in enumerate(cols):
            for c2 in cols[i + 1:]:
                key = (c1, c2)
                result[key] = self.data[c1].rolling(window).corr(self.data[c2])
        return result

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def plot(self, title: str | None = None, **kwargs) -> Chart:
        """Return a Chart with all columns plotted as time series."""
        from tools.charts import Chart

        chart = Chart()
        chart.time_series(self, title=title, **kwargs)
        return chart

    def heatmap(self, metric: str = "correlation", **kwargs) -> Chart:
        """Return a correlation or covariance heatmap Chart."""
        from tools.charts import Chart

        if metric == "correlation":
            matrix = self.correlation()
        elif metric == "covariance":
            matrix = self.covariance()
        else:
            raise ValueError(f"metric must be 'correlation' or 'covariance', got {metric!r}")

        chart = Chart(figsize=(max(6, len(self.columns)), max(5, len(self.columns))))
        chart.heatmap(matrix, **kwargs)
        return chart

    def to_excel(self, wb: NotebookWorkbook, sheet_name: str) -> None:
        """Write this Panel to an Excel sheet in *wb*."""
        df = self.data.reset_index()
        df.columns = ["date"] + list(self.data.columns)
        wb.write(sheet_name, df)
