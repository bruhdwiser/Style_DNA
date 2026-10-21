"""Color harmony utilities for outfit scoring.

Ported from StyleSenseAI outfits/color.py — pure math, no I/O.
Computes perceptual color distance via CIE-Lab and hue harmony via HCL.
"""

from __future__ import annotations

import math
from typing import Any


NAMED_COLORS: dict[str, tuple[float, float, float]] = {
    "black": (0.1, 0.1, 0.1),
    "white": (0.95, 0.95, 0.95),
    "navy": (0.05, 0.1, 0.25),
    "blue": (0.15, 0.35, 0.7),
    "dark blue": (0.08, 0.18, 0.4),
    "sky blue": (0.5, 0.7, 0.9),
    "indigo": (0.2, 0.15, 0.55),
    "gray": (0.5, 0.5, 0.5),
    "grey": (0.5, 0.5, 0.5),
    "pink": (0.9, 0.6, 0.7),
    "blush": (0.87, 0.62, 0.62),
    "green": (0.2, 0.5, 0.3),
    "sage": (0.55, 0.65, 0.55),
    "olive": (0.4, 0.45, 0.2),
    "red": (0.8, 0.15, 0.15),
    "cream": (0.96, 0.94, 0.88),
    "ivory": (0.98, 0.96, 0.9),
    "beige": (0.92, 0.88, 0.78),
    "tan": (0.82, 0.71, 0.55),
    "brown": (0.45, 0.3, 0.2),
    "burgundy": (0.45, 0.1, 0.2),
    "maroon": (0.5, 0.0, 0.0),
    "mustard": (0.8, 0.6, 0.2),
    "yellow": (0.95, 0.85, 0.2),
    "teal": (0.18, 0.45, 0.45),
    "orange": (0.95, 0.5, 0.1),
    "coral": (0.95, 0.45, 0.4),
    "purple": (0.5, 0.2, 0.6),
    "lavender": (0.75, 0.65, 0.85),
    "silver": (0.75, 0.75, 0.75),
    "gold": (0.85, 0.75, 0.3),
    "nude": (0.89, 0.74, 0.60),
    "champagne": (0.97, 0.91, 0.81),
    "pastel": (0.94, 0.92, 0.88),
    "pastel_pink": (1.0, 0.82, 0.86),
    "pastel pink": (1.0, 0.82, 0.86),
    "rust": (0.72, 0.25, 0.05),
    "camel": (0.76, 0.60, 0.42),
    "khaki": (0.76, 0.69, 0.57),
    "emerald": (0.15, 0.55, 0.35),
    "charcoal": (0.21, 0.27, 0.31),
    "wine": (0.45, 0.18, 0.22),
    "taupe": (0.55, 0.52, 0.54),
    "terracotta": (0.80, 0.36, 0.27),
}

FASHION_NEUTRALS: frozenset[str] = frozenset({
    "black",
    "white",
    "gray",
    "grey",
    "charcoal",
    "silver",
    "cream",
    "ivory",
    "beige",
    "tan",
    "nude",
    "champagne",
    "taupe",
    "camel",
    "khaki",
    "navy",
    "dark blue",
    "brown",
    "gold",
    "pastel",
})


def _extract_color_name(value: Any) -> str:
    """Normalize a color string into a clean lowercase name if applicable."""
    if isinstance(value, str):
        c = value.strip().lower().replace("-", "_").lstrip("#")
        return c
    return ""


def _normalize_hex(value: Any) -> tuple[float, float, float]:
    """Convert a hex string, named color, or 3-tuple to an RGB 0..1 triple."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (ValueError, TypeError):
            return (0.8, 0.8, 0.8)

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in NAMED_COLORS:
            return NAMED_COLORS[cleaned]

        cleaned_norm = cleaned.replace("-", "_")
        if cleaned_norm in NAMED_COLORS:
            return NAMED_COLORS[cleaned_norm]

        hex_value = cleaned.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) == 6 and all(c in "0123456789abcdef" for c in hex_value):
            try:
                return (
                    int(hex_value[0:2], 16) / 255.0,
                    int(hex_value[2:4], 16) / 255.0,
                    int(hex_value[4:6], 16) / 255.0,
                )
            except ValueError:
                pass

    return (0.8, 0.8, 0.8)


def _rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Approximate sRGB → CIE-Lab conversion (D65 illuminant)."""
    r, g, b = rgb
    # Linearise sRGB
    r = pow(r, 2.2) if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = pow(g, 2.2) if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = pow(b, 2.2) if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4

    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    x_n, y_n, z_n = 0.95047, 1.0, 1.08883

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    l_val = 116 * _f(y / y_n) - 16
    a_val = 500 * (_f(x / x_n) - _f(y / y_n))
    b_val = 200 * (_f(y / y_n) - _f(z / z_n))
    return (l_val, a_val, b_val)


def _lab_to_hcl(lab: tuple[float, float, float]) -> tuple[float, float]:
    """Extract hue and chroma from Lab coordinates."""
    _, a, b = lab
    c = math.sqrt(a * a + b * b)
    h = math.degrees(math.atan2(b, a)) if c != 0 else 0.0
    h = (h + 360.0) % 360.0
    return h, c


def color_distance_lab(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    """Euclidean ΔE in Lab space."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def harmony_score(color_a: Any, color_b: Any) -> float:
    """Return a 0..1 color harmony score grounded in fashion color theory.

    Fashion harmony rules:
    1. Neutral + Neutral: Inherently classic and sophisticated (0.94; 1.0 if identical).
    2. Neutral + Accent: Neutrals naturally ground any accent color (0.88).
    3. Accent + Accent: Evaluated via HCL hue wheel (analogous, complementary, triadic).
    """
    name_a = _extract_color_name(color_a)
    name_b = _extract_color_name(color_b)

    is_neut_a = name_a in FASHION_NEUTRALS
    is_neut_b = name_b in FASHION_NEUTRALS

    # 1. Neutral + Neutral
    if is_neut_a and is_neut_b:
        if name_a == name_b:
            return 1.0
        return 0.94

    # 2. Neutral + Accent
    if is_neut_a or is_neut_b:
        return 0.88

    # 3. Accent + Accent
    lab_a = _rgb_to_lab(_normalize_hex(color_a))
    lab_b = _rgb_to_lab(_normalize_hex(color_b))
    hcl_a = _lab_to_hcl(lab_a)
    hcl_b = _lab_to_hcl(lab_b)
    hue_delta = abs((hcl_a[0] - hcl_b[0]) % 360.0)
    hue_delta = min(hue_delta, 360.0 - hue_delta)

    # Analogous (<= 45 deg)
    if hue_delta <= 45.0:
        score = 0.92 - (hue_delta / 45.0) * 0.07
    # Complementary (150 - 210 deg)
    elif 150.0 <= hue_delta <= 210.0:
        comp_dist = abs(hue_delta - 180.0)
        score = 0.90 - (comp_dist / 30.0) * 0.08
    # Triadic (105 - 135 deg)
    elif 105.0 <= hue_delta <= 135.0:
        tri_dist = abs(hue_delta - 120.0)
        score = 0.84 - (tri_dist / 15.0) * 0.06
    else:
        score = max(0.40, 0.75 - (hue_delta / 180.0) * 0.35)

    return round(max(0.0, min(1.0, score)), 3)


def palette_harmony(colors: list[Any]) -> float:
    """Average the pairwise harmony across a palette of colour values."""
    if not colors:
        return 0.5
    if len(colors) == 1:
        return 1.0
    scores: list[float] = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            scores.append(harmony_score(colors[i], colors[j]))
    return round(sum(scores) / len(scores), 3) if scores else 0.5
