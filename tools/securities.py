"""Asset class hierarchy for yfinance-backed securities.

BondMath  — static bond math utilities (duration, convexity, DV01, total return)
Ticker    — base yfinance wrapper; lazy-loads prices as a Panel
FI_ETF    — fixed-income ETF with rate sensitivity, carry, duration methods
Equity    — equity with rolling beta, relative return
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from tools.series import Panel, TimeSeries

if TYPE_CHECKING:
    from tools.charts import Chart
    from tools.excel import NotebookWorkbook


# ---------------------------------------------------------------------------
# BondMath — static utilities
# ---------------------------------------------------------------------------

class BondMath:
    """Static bond math used by FI_ETF and treasury notebooks."""

    @staticmethod
    def modified_duration(ytm_pct: float, maturity_yrs: float) -> float:
        """Modified duration of a par coupon bond (annual coupon, simplified).

        Args:
            ytm_pct:     yield to maturity in percent (e.g. 4.5 for 4.5%)
            maturity_yrs: time to maturity in years

        Returns:
            Modified duration in years.
        """
        if ytm_pct < 1e-6 or maturity_yrs < 0.25:
            return maturity_yrs
        y = ytm_pct / 100
        mac = (1 - (1 + y) ** (-maturity_yrs)) / y
        return mac / (1 + y)

    @staticmethod
    def bond_price(
        ytm_pct: float,
        maturity_yrs: float,
        coupon_pct: float | None = None,
        freq: int = 2,
    ) -> float:
        """Price a fixed-coupon bond given a yield.

        Args:
            ytm_pct:     discount yield in percent (e.g. 4.5)
            maturity_yrs: years to maturity
            coupon_pct:  annual coupon rate in percent; defaults to ytm_pct
                         (i.e. a par bond at issuance)
            freq:        coupon payments per year (2 = semi-annual)

        Returns:
            Clean price per $100 face value.
        """
        cpn = (coupon_pct if coupon_pct is not None else ytm_pct) / 100 / freq
        y = ytm_pct / 100 / freq
        n = int(round(maturity_yrs * freq))
        if n == 0:
            return 100.0
        pv_coupons = sum(cpn * 100 / (1 + y) ** t for t in range(1, n + 1))
        pv_principal = 100 / (1 + y) ** n
        return pv_coupons + pv_principal

    @staticmethod
    def par_bond_price(ytm_pct: float, maturity_yrs: float, freq: int = 2) -> float:
        """Price of a par-coupon bond (coupon = ytm at issuance) at *ytm_pct*.

        Since coupon is fixed at issuance, this price will differ from 100
        only when ytm has changed.  Use bond_price() for general pricing.
        """
        return BondMath.bond_price(ytm_pct, maturity_yrs, coupon_pct=ytm_pct, freq=freq)

    @staticmethod
    def convexity(ytm_pct: float, maturity_yrs: float, dy: float = 1e-4) -> float:
        """Convexity of a par-coupon bond, estimated by bumping yield by *dy* (decimal).

        dy is in decimal (e.g. 1e-4 = 1bp).  The coupon is fixed at ytm_pct.
        """
        p0 = BondMath.bond_price(ytm_pct, maturity_yrs, coupon_pct=ytm_pct)
        p_up = BondMath.bond_price(ytm_pct + dy * 100, maturity_yrs, coupon_pct=ytm_pct)
        p_dn = BondMath.bond_price(ytm_pct - dy * 100, maturity_yrs, coupon_pct=ytm_pct)
        if p0 == 0:
            return 0.0
        return (p_up + p_dn - 2 * p0) / (p0 * dy ** 2)

    @staticmethod
    def dv01(ytm_pct: float, maturity_yrs: float) -> float:
        """Dollar value of a 1bp yield move for a par-coupon bond (per $100 face).

        Coupon is fixed at ytm_pct; only the discount rate is bumped.
        """
        p_up = BondMath.bond_price(ytm_pct - 0.01, maturity_yrs, coupon_pct=ytm_pct)
        p_dn = BondMath.bond_price(ytm_pct + 0.01, maturity_yrs, coupon_pct=ytm_pct)
        return (p_up - p_dn) / 2

    @staticmethod
    def total_return(
        y_start: float,
        y_end: float,
        y_rolled: float,
        duration: float,
        T_hold: float = 1.0,
    ) -> dict[str, float]:
        """Approximate total return decomposition for a bond/ETF.

        Args:
            y_start:  starting yield (%)
            y_end:    ending yield (%)
            y_rolled: yield of the bond after rolling down the curve for T_hold
            duration: modified duration at start
            T_hold:   holding period in years

        Returns dict with keys: carry, roll_down, price_return, total (all in %).
        """
        carry = y_start * T_hold
        roll_down = -duration * (y_rolled - y_start)
        price_return = -duration * (y_end - y_start)
        total = carry + roll_down + price_return
        return {
            "carry": carry,
            "roll_down": roll_down,
            "price_return": price_return,
            "total": total,
        }


# ---------------------------------------------------------------------------
# Ticker — base class
# ---------------------------------------------------------------------------

class Ticker:
    """yfinance-backed asset.  Prices and returns are lazy-loaded on first access.

    Args:
        symbol: yfinance ticker (e.g. "AGG", "AAPL")
        start:  start date for history (string or date; None = max available)
        end:    end date for history
        field:  OHLCV field to use as the price series (default "Close")
    """

    def __init__(
        self,
        symbol: str,
        start=None,
        end=None,
        field: str = "Close",
    ):
        self.symbol = symbol.upper()
        self.start = start
        self.end = end
        self.field = field
        self._prices_cache: Panel | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.symbol!r})"

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _fetch(self) -> Panel:
        """Download price data from yfinance and return as Panel."""
        import yfinance as yf

        raw = yf.download(
            self.symbol,
            start=self.start,
            end=self.end,
            auto_adjust=True,
            progress=False,
        )
        if raw.empty:
            raise ValueError(f"No data returned for ticker {self.symbol!r}.")

        # yfinance returns multi-level columns for single ticker in newer versions
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        price_col = self.field if self.field in raw.columns else raw.columns[0]
        series = raw[price_col].rename(self.symbol)
        series.index = pd.to_datetime(series.index)
        df = series.to_frame().dropna()
        return Panel(df)

    @property
    def prices(self) -> Panel:
        """Closing price Panel (lazy, cached)."""
        if self._prices_cache is None:
            self._prices_cache = self._fetch()
        return self._prices_cache

    @property
    def returns(self) -> Panel:
        """Daily arithmetic returns Panel (pct_change, NaN row dropped)."""
        return self.prices.pct_change()

    @property
    def log_returns(self) -> Panel:
        """Daily log returns Panel."""
        return self.prices.pct_change(log=True)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def stats(self, rf: float = 0.0, periods: int = 252) -> pd.DataFrame:
        """Annualised performance stats for this ticker.

        rf should be in decimal (e.g. 0.045 for 4.5%).
        """
        return self.returns.stats(rf=rf, periods=periods)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def plot(self, **kwargs) -> Chart:
        """Plot prices as a time series."""
        return self.prices.plot(title=self.symbol, **kwargs)

    def to_excel(self, wb: NotebookWorkbook, prefix: str = "") -> None:
        """Write Prices, Returns, and Stats sheets to *wb*."""
        tag = f"{prefix}{self.symbol} " if prefix else f"{self.symbol} "
        self.prices.to_excel(wb, f"{tag}Prices"[:31])
        self.returns.to_excel(wb, f"{tag}Returns"[:31])
        wb.write(f"{tag}Stats"[:31], self.stats().reset_index().rename(columns={"index": "Metric"}))


# ---------------------------------------------------------------------------
# FI_ETF — fixed-income ETF
# ---------------------------------------------------------------------------

class FI_ETF(Ticker):
    """Fixed-income ETF with rate-sensitivity and carry analytics.

    Args:
        symbol:   yfinance ticker (e.g. "AGG", "TLT", "IEF")
        duration: known effective duration in years; if None, estimated
                  by regressing returns on rate changes.
        start:    start date for price history
        end:      end date for price history
    """

    def __init__(
        self,
        symbol: str,
        duration: float | None = None,
        start=None,
        end=None,
    ):
        super().__init__(symbol, start=start, end=end)
        self._duration = duration

    def rate_sensitivity(
        self, rate_series: pd.Series | TimeSeries
    ) -> dict[str, float]:
        """OLS regression of daily returns on daily yield changes.

        Returns dict with implied_duration, r_squared, beta, alpha (annualised).

        The implied duration ≈ -beta because a 1pp rise in yields causes
        roughly duration% price decline.
        """
        from scipy import stats as scipy_stats

        y_series = rate_series.data if isinstance(rate_series, TimeSeries) else rate_series
        dy = y_series.diff().dropna()
        rets = self.returns.data[self.symbol]

        aligned = pd.concat([rets, dy], axis=1).dropna()
        aligned.columns = ["ret", "dy"]

        slope, intercept, r, _, _ = scipy_stats.linregress(
            aligned["dy"], aligned["ret"]
        )
        return {
            "implied_duration": -slope * 100,  # convert to years
            "beta": slope,
            "alpha_ann": intercept * 252,
            "r_squared": r ** 2,
        }

    def carry_analysis(
        self, yield_series: pd.Series | TimeSeries, lookback_years: int = 1
    ) -> pd.DataFrame:
        """Decompose trailing return into income (carry) and price change.

        Uses end-of-period yield as a proxy for income earned over the period.
        This is a simplified approximation: carry ≈ avg yield × T_hold,
        price_change = total_return − carry.
        """
        y = yield_series.data if isinstance(yield_series, TimeSeries) else yield_series
        rets = self.returns.data[self.symbol]

        aligned = pd.concat([rets, y.rename("yield")], axis=1).dropna()
        end = aligned.index[-1]
        start = end - pd.DateOffset(years=lookback_years)
        window = aligned[aligned.index >= start]

        total_ret = (1 + window["ret"]).prod() - 1
        avg_yield = window["yield"].mean() / 100
        carry = avg_yield * lookback_years
        price_change = total_ret - carry

        return pd.DataFrame(
            {
                "Component": ["Carry (income)", "Price Change", "Total Return"],
                "Return (%)": [carry * 100, price_change * 100, total_ret * 100],
            }
        )

    def duration_adjusted_returns(self, target_dur: float) -> Panel:
        """Scale daily returns to a common target duration for comparability.

        Useful when comparing ETFs with different durations on equal footing.
        Requires a known duration (passed at construction) or estimated via
        rate_sensitivity().
        """
        dur = self._duration
        if dur is None:
            raise ValueError(
                f"{self.symbol}: duration not set.  Pass duration= at construction "
                "or call rate_sensitivity() to estimate it first."
            )
        if dur == 0:
            raise ValueError("Duration cannot be zero.")
        scale = target_dur / dur
        adj = self.returns.data * scale
        adj.columns = [f"{self.symbol}_dur{target_dur}"]
        return Panel(adj)

    def rate_correlation(self, *fred_series_ids: str) -> pd.DataFrame:
        """Correlation table between this ETF's returns and FRED series changes.

        Loads each FRED series from the local cache and diffs it.
        """
        from tools.data import load_fred

        rets = self.returns.data[self.symbol].rename(self.symbol)
        pieces = [rets]
        for sid in fred_series_ids:
            s = load_fred(sid).diff().dropna().rename(sid)
            pieces.append(s)

        combined = pd.concat(pieces, axis=1).dropna()
        return combined.corr()

    def key_rate_durations(
        self,
        *fred_ids: str,
        start: str | None = None,
    ) -> pd.Series:
        """Empirical key rate durations via multivariate OLS.

        Regresses daily ETF returns on simultaneous daily changes at each
        supplied rate tenor.  KRD_k = -β_k × 100.

        Standard tenors: 'DGS2', 'DGS5', 'DGS10', 'DGS30'

        Args:
            *fred_ids: FRED series IDs for each key rate tenor, in order.
            start:     optional start date to restrict the regression window.

        Returns:
            pd.Series indexed by FRED ID, values in years (KRD per tenor).
            Also includes 'alpha_ann', 'r_squared', 'total_duration' keys.
        """
        import statsmodels.api as sm
        from tools.data import load_fred

        rets = self.returns.data[self.symbol]
        rate_changes = {}
        for sid in fred_ids:
            s = load_fred(sid)
            if start:
                s = s[s.index >= pd.Timestamp(start)]
            rate_changes[sid] = s.diff().dropna()

        aligned = pd.concat([rets, *rate_changes.values()], axis=1).dropna()
        aligned.columns = [self.symbol] + list(fred_ids)

        if start:
            aligned = aligned[aligned.index >= pd.Timestamp(start)]

        y = aligned[self.symbol]
        X = sm.add_constant(aligned[list(fred_ids)])
        result = sm.OLS(y, X).fit()

        krd = pd.Series(
            {sid: -result.params[sid] * 100 for sid in fred_ids},
            name=self.symbol,
        )
        krd["alpha_ann"] = result.params.get("const", 0.0) * 252
        krd["r_squared"] = result.rsquared
        krd["total_duration"] = krd[list(fred_ids)].sum()
        return krd


# ---------------------------------------------------------------------------
# Equity
# ---------------------------------------------------------------------------

class Equity(Ticker):
    """Equity security with beta and relative-return analytics."""

    def beta(
        self,
        benchmark: Ticker | pd.Series,
        window: int = 252,
    ) -> pd.Series:
        """Rolling beta vs benchmark returns.

        Args:
            benchmark: a Ticker (uses .returns) or a pd.Series of returns.
            window:    rolling window in trading days.

        Returns:
            pd.Series of rolling beta values.
        """
        bm = (
            benchmark.returns.data.iloc[:, 0]
            if isinstance(benchmark, Ticker)
            else benchmark
        )
        asset_rets = self.returns.data[self.symbol]

        aligned = pd.concat([asset_rets, bm.rename("bm")], axis=1).dropna()
        cov = aligned[self.symbol].rolling(window).cov(aligned["bm"])
        var = aligned["bm"].rolling(window).var()
        return (cov / var).rename(f"{self.symbol}_beta")

    def relative_return(self, benchmark: Ticker) -> Panel:
        """Cumulative return of this equity minus the benchmark (alpha series)."""
        asset_cum = self.returns.cumulative_returns()
        bm_cum = benchmark.returns.cumulative_returns()
        aligned = pd.concat(
            [asset_cum.data[self.symbol], bm_cum.data[benchmark.symbol]], axis=1
        ).dropna()
        rel = (aligned[self.symbol] - aligned[benchmark.symbol]).rename(
            f"{self.symbol}_vs_{benchmark.symbol}"
        )
        return Panel(rel.to_frame())
