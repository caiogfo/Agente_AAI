"""XP house-style visual tokens (emulated, not official XP assets).

Palette: XP yellow + black + neutral grays. Centralized here so charts and the
PDF stay consistent and the brand is easy to re-skin per advisor/white-label.
"""

# Core palette
XP_YELLOW = "#FFC700"      # primary accent (XP-like yellow)
XP_YELLOW_DK = "#E0A800"   # darker yellow for outlines/hover
XP_BLACK = "#0D0D0D"       # near-black (headers, text)
XP_GRAPHITE = "#2B2B2B"    # secondary dark
XP_GRAY = "#6B6B6B"        # muted text
XP_GRAY_LT = "#E9E9E9"     # light fills / table zebra
XP_WHITE = "#FFFFFF"
XP_BG = "#FAFAFA"          # page background tint

# Semantic colors for performance figures
POSITIVE = "#1B8A5A"       # green
NEGATIVE = "#C0392B"       # red
NEUTRAL = XP_GRAY

# Chart categorical sequence (yellow-forward, brand-consistent)
CHART_SEQUENCE = [XP_YELLOW, XP_BLACK, XP_GRAPHITE, XP_YELLOW_DK, XP_GRAY, "#B8961F"]

FONT_FAMILY = "Helvetica"  # widely available; reportlab core font


def signed_color(value: float) -> str:
    if value > 0:
        return POSITIVE
    if value < 0:
        return NEGATIVE
    return NEUTRAL
