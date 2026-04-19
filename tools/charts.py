"""Consistent plot builder for financial analysis notebooks.

Chart wraps matplotlib with a standard style, colour palette, and common
financial plot types.  All plotting methods return self for chaining.

Usage (single panel)::

    Chart().time_series(panel, title="Treasury Yields").save("output/yields.png")

Usage (multi-panel)::

    Chart(1, 2, figsize=(14, 5)) \\
        .time_series(prices, ax=(0, 0), title="Prices") \\
        .heatmap(corr_df, ax=(0, 1)) \\
        .tight().show()
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tools.palette import Palette
from tools.palette import NAVY, GOLD, COPPER, COBALT, AMBER, SLATE, HORIZON, MOSS

if TYPE_CHECKING:
    from tools.series import Panel, TimeSeries

STYLE = "seaborn-v0_8-darkgrid"
PALETTE = Palette.SERIES


def _resolve_data(
    data: Panel | TimeSeries | pd.DataFrame | pd.Series,
) -> pd.DataFrame:
    """Return a plain DataFrame from any supported input type."""
    # import locally to avoid circular at module level
    from tools.series import Panel, TimeSeries

    if isinstance(data, Panel):
        return data.data
    if isinstance(data, TimeSeries):
        return data.data.to_frame()
    if isinstance(data, pd.Series):
        return data.to_frame()
    return data  # already DataFrame


class Chart:
    """Matplotlib-backed plot builder with consistent financial styling.

    Args:
        nrows:   number of subplot rows (default 1)
        ncols:   number of subplot columns (default 1)
        figsize: (width, height); auto-sized as (7*ncols, 4.5*nrows) if None
        style:   matplotlib style string
    """

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] | None = None,
        style: str = STYLE,
    ):
        try:
            plt.style.use(style)
        except OSError:
            pass  # fall back to default if style unavailable

        figsize = figsize or (7 * ncols, 4.5 * nrows)
        self.fig, _axes = plt.subplots(nrows, ncols, figsize=figsize)
        self._nrows = nrows
        self._ncols = ncols

        # Normalise axes to always be a 2D array
        if nrows == 1 and ncols == 1:
            self._axes = np.array([[_axes]])
        elif nrows == 1:
            self._axes = np.array([_axes])
        elif ncols == 1:
            self._axes = np.array([[a] for a in _axes])
        else:
            self._axes = _axes

    # ------------------------------------------------------------------
    # Axis resolution
    # ------------------------------------------------------------------

    def ax(self, row: int = 0, col: int = 0) -> plt.Axes:
        """Return the matplotlib Axes at position (row, col)."""
        return self._axes[row, col]

    def _get_ax(self, ax_spec) -> plt.Axes:
        """Resolve ax= argument: None → (0,0), tuple → row/col, Axes → as-is."""
        if ax_spec is None:
            return self._axes[0, 0]
        if isinstance(ax_spec, tuple):
            return self._axes[ax_spec[0], ax_spec[1]]
        return ax_spec  # already a matplotlib Axes

    # ------------------------------------------------------------------
    # Plot methods — all return self
    # ------------------------------------------------------------------

    def time_series(
        self,
        data: Panel | TimeSeries | pd.DataFrame | pd.Series,
        title: str | None = None,
        ylabel: str | None = None,
        xlabel: str | None = None,
        linewidth: float = 1.0,
        ax=None,
        **kwargs,
    ) -> Chart:
        """Plot one or more time series as lines."""
        _ax = self._get_ax(ax)
        df = _resolve_data(data)

        for i, col in enumerate(df.columns):
            color = PALETTE[i % len(PALETTE)]
            _ax.plot(
                df.index,
                df[col],
                label=col,
                color=color,
                linewidth=linewidth,
                **kwargs,
            )

        if title:
            _ax.set_title(title, fontsize=12)
        if ylabel:
            _ax.set_ylabel(ylabel)
        if xlabel:
            _ax.set_xlabel(xlabel)
        if len(df.columns) > 1:
            _ax.legend(fontsize=9)

        return self

    def histogram(
        self,
        data: TimeSeries | pd.Series,
        bins: int = 50,
        vlines: list[float] | None = None,
        title: str | None = None,
        xlabel: str | None = None,
        ax=None,
        **kwargs,
    ) -> Chart:
        """Distribution histogram with optional vertical reference lines."""
        _ax = self._get_ax(ax)
        from tools.series import TimeSeries

        series = data.data if isinstance(data, TimeSeries) else data
        label = series.name or "value"

        _ax.hist(
            series.dropna(),
            bins=bins,
            alpha=0.75,
            color=NAVY,
            edgecolor="none",
            label=label,
            **kwargs,
        )

        if vlines:
            for v in vlines:
                _ax.axvline(v, color="black", linestyle="--", linewidth=0.8)

        if title:
            _ax.set_title(title, fontsize=12)
        if xlabel:
            _ax.set_xlabel(xlabel)
        _ax.set_ylabel("Frequency")

        return self

    def heatmap(
        self,
        matrix: pd.DataFrame,
        fmt: str = ".2f",
        cmap: str = "RdYlGn",
        title: str | None = None,
        ax=None,
    ) -> Chart:
        """Annotated correlation/covariance heatmap."""
        import matplotlib.colors as mcolors

        _ax = self._get_ax(ax)
        n = len(matrix)
        vmax = 1.0 if matrix.values.max() <= 1.0 else matrix.values.max()
        vmin = -vmax if matrix.values.min() < 0 else 0

        im = _ax.imshow(
            matrix.values,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            aspect="auto",
        )
        self.fig.colorbar(im, ax=_ax, shrink=0.8)

        _ax.set_xticks(range(n))
        _ax.set_yticks(range(n))
        _ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=9)
        _ax.set_yticklabels(matrix.index, fontsize=9)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                val = matrix.values[i, j]
                if not np.isnan(val):
                    text_color = "white" if abs(val) > 0.6 * vmax else "black"
                    _ax.text(
                        j, i, format(val, fmt),
                        ha="center", va="center",
                        fontsize=8, color=text_color,
                    )

        if title:
            _ax.set_title(title, fontsize=12)

        return self

    def percentile_fan(
        self,
        paths: np.ndarray,
        index=None,
        percentiles: tuple = (5, 25, 50, 75, 95),
        color: str = NAVY,
        title: str | None = None,
        ax=None,
    ) -> Chart:
        """Fan chart showing percentile bands across Monte Carlo paths.

        Args:
            paths:       2D array (n_paths × n_timesteps)
            index:       x-axis values; defaults to integer range
            percentiles: iterable of percentile values (must include 50 for median)
            color:       base colour for bands
        """
        _ax = self._get_ax(ax)
        x = index if index is not None else np.arange(paths.shape[1])
        pcts = {p: np.percentile(paths, p, axis=0) for p in percentiles}

        sorted_p = sorted(percentiles)
        n = len(sorted_p)
        mid = n // 2

        # Fill bands symmetrically around median
        for i in range(mid):
            lo, hi = sorted_p[i], sorted_p[n - 1 - i]
            alpha = 0.10 + 0.10 * i
            _ax.fill_between(x, pcts[lo], pcts[hi], alpha=alpha, color=color)

        # Median line
        if 50 in pcts:
            _ax.plot(x, pcts[50], color=color, linewidth=1.5, label="Median")

        # Legend for outer bands
        if sorted_p[0] != 50:
            from matplotlib.patches import Patch
            _ax.legend(
                handles=[
                    Patch(color=color, alpha=0.2, label=f"P{sorted_p[0]}–P{sorted_p[-1]}"),
                    Patch(color=color, alpha=0.35, label=f"P{sorted_p[1]}–P{sorted_p[-2]}"),
                    plt.Line2D([0], [0], color=color, label="Median"),
                ],
                fontsize=8,
            )

        if title:
            _ax.set_title(title, fontsize=12)

        return self

    def shade_regimes(
        self,
        dates,
        states: np.ndarray,
        labels: dict | None = None,
        colors: list[str] | None = None,
        alpha: float = 0.25,
        ax=None,
    ) -> Chart:
        """Shade background of an axes by regime state.

        Args:
            dates:  date-like index aligned with *states*
            states: integer array of regime labels
            labels: optional {state_int: label_str} dict for legend
            colors: optional per-state colour list
            alpha:  fill transparency
        """
        _ax = self._get_ax(ax)
        regime_colors = colors or Palette.REGIME
        unique_states = np.unique(states)

        ymin, ymax = _ax.get_ylim()
        if ymin == 0.0 and ymax == 1.0:
            ymin, ymax = -1e10, 1e10  # fallback before data is plotted

        from matplotlib.patches import Patch
        legend_handles = []

        for s in unique_states:
            mask = states == s
            color = regime_colors[int(s) % len(regime_colors)]
            _ax.fill_between(
                dates, ymin, ymax,
                where=mask,
                alpha=alpha,
                color=color,
                interpolate=True,
            )
            if labels:
                legend_handles.append(
                    Patch(color=color, alpha=alpha + 0.1, label=labels.get(s, f"State {s}"))
                )

        if legend_handles:
            _ax.legend(handles=legend_handles, fontsize=8)

        return self

    def twin_axis(
        self,
        data: TimeSeries | pd.Series,
        label: str | None = None,
        color: str = COPPER,
        linewidth: float = 1.0,
        ax=None,
        **kwargs,
    ) -> Chart:
        """Overlay a series on a secondary y-axis of the selected axes."""
        from tools.series import TimeSeries

        _ax = self._get_ax(ax)
        ax2 = _ax.twinx()
        series = data.data if isinstance(data, TimeSeries) else data
        ax2.plot(
            series.index,
            series.values,
            color=color,
            linewidth=linewidth,
            label=label or (series.name or ""),
            **kwargs,
        )
        if label:
            ax2.set_ylabel(label, color=color)
        ax2.tick_params(axis="y", labelcolor=color)
        return self

    def scatter(
        self,
        x: pd.Series,
        y: pd.Series,
        label: str | None = None,
        color: str | None = None,
        alpha: float = 0.6,
        ax=None,
        **kwargs,
    ) -> Chart:
        """Scatter plot of two series (aligned on their index)."""
        _ax = self._get_ax(ax)
        aligned = pd.concat([x, y], axis=1).dropna()
        _ax.scatter(
            aligned.iloc[:, 0],
            aligned.iloc[:, 1],
            label=label,
            color=color or NAVY,
            alpha=alpha,
            s=18,
            **kwargs,
        )
        _ax.set_xlabel(x.name or "x")
        _ax.set_ylabel(y.name or "y")
        if label:
            _ax.legend(fontsize=9)
        return self

    # ------------------------------------------------------------------
    # Annotations / finalization
    # ------------------------------------------------------------------

    def title(self, text: str, ax=None) -> Chart:
        self._get_ax(ax).set_title(text, fontsize=12)
        return self

    def labels(
        self,
        xlabel: str | None = None,
        ylabel: str | None = None,
        ax=None,
    ) -> Chart:
        _ax = self._get_ax(ax)
        if xlabel:
            _ax.set_xlabel(xlabel)
        if ylabel:
            _ax.set_ylabel(ylabel)
        return self

    def legend(self, ax=None, **kwargs) -> Chart:
        self._get_ax(ax).legend(fontsize=9, **kwargs)
        return self

    def tight(self) -> Chart:
        plt.tight_layout()
        return self

    def save(self, path: str | Path, dpi: int = 150) -> Chart:
        """Save figure to file.  Creates parent directories as needed."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(out, dpi=dpi, bbox_inches="tight")
        return self

    def show(self) -> Chart:
        plt.tight_layout()
        plt.show()
        return self

    def close(self) -> None:
        """Close the underlying figure to free memory."""
        plt.close(self.fig)
