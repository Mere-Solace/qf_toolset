"""Investment-banking colour palette for financial analysis notebooks.

All notebooks and Chart instances must draw colours from this module — never
hard-code hex strings or named matplotlib colours inline.

Usage::

    from tools.palette import NAVY, GOLD, Palette

    # Single named colour
    ax.plot(x, y, color=NAVY)

    # Ordered cycle for multi-series plots
    for col, color in zip(df.columns, Palette.SERIES):
        ax.plot(df.index, df[col], color=color)

    # n-shade gradient within a colour family
    colors = Palette.navy(5)    # dark → light
    colors = Palette.gold(4)
    colors = Palette.gray(3)

    # Arbitrary two-colour gradient
    colors = Palette.gradient(NAVY, GOLD, n=6)
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Core named colours
# ---------------------------------------------------------------------------

# Blues / navies
NAVY        = "#0D2240"   # deep navy — primary series / backgrounds
STEEL       = "#1E4E8C"   # medium navy-blue — secondary series
COBALT      = "#2E75B6"   # bright cobalt — highlight / accent line
HORIZON     = "#5B9BD5"   # light steel blue — tertiary series / bands
MIST        = "#D6DCE4"   # very light blue-grey — fill / shading

# Golds / ambers
GOLD        = "#C9A84C"   # classic IB gold — primary accent / second series
AMBER       = "#A67C24"   # dark amber — deeper gold variant
BRONZE      = "#7B5E2A"   # warm dark brown-gold
CHAMPAGNE   = "#E8D5A3"   # pale gold — fills / bands

# Neutrals
CHARCOAL    = "#1F2933"   # near-black — axes, primary text lines
GRAPHITE    = "#4A5568"   # dark grey — secondary text / grid
SLATE       = "#718096"   # medium grey-blue
SILVER      = "#A0AEC0"   # light grey — minor grid / legend text
PEARL       = "#E2E8F0"   # very light grey — panel backgrounds
IVORY       = "#F7F4EE"   # off-white

# Accent / risk colours (use sparingly)
COPPER      = "#C05621"   # warm red-orange — loss / risk / short
MOSS        = "#276749"   # dark green — gain / long / positive


# ---------------------------------------------------------------------------
# Palette — semantic groupings and gradient helpers
# ---------------------------------------------------------------------------

class Palette:
    """Semantic colour groups and gradient generators.

    Class attributes are the primary interface; methods generate gradients.
    """

    # Default ordered cycle for multi-series plots.
    # Designed to be visually distinct at up to 8 series.
    SERIES: list[str] = [
        NAVY,
        GOLD,
        COBALT,
        AMBER,
        SLATE,
        COPPER,
        HORIZON,
        MOSS,
    ]

    # Pre-built 5-stop gradients (index 0 = darkest)
    NAVY_GRADIENT:  list[str] = [NAVY, STEEL, COBALT, HORIZON, MIST]
    GOLD_GRADIENT:  list[str] = [BRONZE, AMBER, GOLD, CHAMPAGNE, IVORY]
    GRAY_GRADIENT:  list[str] = [CHARCOAL, GRAPHITE, SLATE, SILVER, PEARL]

    # Positive / negative fill pair (e.g. above/below zero)
    POS_COLOR: str = COBALT
    NEG_COLOR: str = COPPER

    # Fan/percentile band base colours
    FAN_PRIMARY:    str = NAVY
    FAN_SECONDARY:  str = GOLD

    # Regime shading cycle (muted for fill_between)
    REGIME: list[str] = [MIST, CHAMPAGNE, PEARL, HORIZON]

    # Heatmap colourmap names (pass to matplotlib)
    HEATMAP_DIVERGING:  str = "RdYlGn"
    HEATMAP_SEQUENTIAL: str = "Blues"

    # ----------------------------------------------------------------
    # Gradient generators
    # ----------------------------------------------------------------

    @staticmethod
    def gradient(hex_a: str, hex_b: str, n: int) -> list[str]:
        """Return *n* hex colours linearly interpolated between *hex_a* and *hex_b*.

        Index 0 = hex_a, index n-1 = hex_b.  Works for any two hex colours.
        """
        if n < 2:
            return [hex_a] * max(n, 1)

        ra, ga, ba = _hex_to_rgb(hex_a)
        rb, gb, bb = _hex_to_rgb(hex_b)

        result = []
        for i in range(n):
            t = i / (n - 1)
            r = round(ra + t * (rb - ra))
            g = round(ga + t * (gb - ga))
            b = round(ba + t * (bb - ba))
            result.append(_rgb_to_hex(r, g, b))
        return result

    @classmethod
    def navy(cls, n: int) -> list[str]:
        """n shades across the navy family (dark → light)."""
        return _sample(cls.NAVY_GRADIENT, n)

    @classmethod
    def gold(cls, n: int) -> list[str]:
        """n shades across the gold family (dark → light)."""
        return _sample(cls.GOLD_GRADIENT, n)

    @classmethod
    def gray(cls, n: int) -> list[str]:
        """n shades across the grey family (dark → light)."""
        return _sample(cls.GRAY_GRADIENT, n)

    @classmethod
    def series(cls, n: int) -> list[str]:
        """Return *n* colours from the default SERIES cycle (wraps if n > 8)."""
        return [cls.SERIES[i % len(cls.SERIES)] for i in range(n)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _sample(stops: list[str], n: int) -> list[str]:
    """Sample *n* colours from a list of gradient stops via interpolation."""
    if n <= 0:
        return []
    if n == 1:
        return [stops[len(stops) // 2]]
    if n >= len(stops):
        # interpolate between first and last stop
        return Palette.gradient(stops[0], stops[-1], n)
    # pick evenly-spaced stops and interpolate between consecutive pairs
    indices = [round(i * (len(stops) - 1) / (n - 1)) for i in range(n)]
    return [stops[i] for i in indices]
