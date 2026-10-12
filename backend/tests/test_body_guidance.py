"""Tests for neutral body guidance derivation and fit scoring."""

from app.routers.style_profile import _derive_body_guidance
from app.styling.body_fit import body_fit


def test_derive_body_guidance_for_hourglass():
    """Verify neutral recommendations derived for Hourglass body type."""
    guidance = _derive_body_guidance("Hourglass")
    assert guidance is not None
    assert guidance["body_type"] == "Hourglass"
    recommendations = guidance["recommendations"]
    assert "neckline" in recommendations
    assert "fit" in recommendations
    # Top neckline pick should be V Neck
    assert "V Neck" in recommendations["neckline"]
    assert "Tailored" in recommendations["fit"]


def test_derive_body_guidance_returns_none_for_missing_shape():
    """Verify missing shape returns None without raising errors."""
    assert _derive_body_guidance(None) is None
    assert _derive_body_guidance("") is None
    assert _derive_body_guidance("UnknownType") is None


def test_body_fit_scoring_neutral_when_shape_omitted():
    """Verify that omitting body shape yields a neutral 0.5 score."""
    score = body_fit(attrs={"neckline": "v_neck", "fit": "tailored"}, shape="")
    assert score == 0.5


def test_body_fit_scoring_with_preferred_attributes():
    """Verify that tailored garments for Hourglass score high (> 0.8)."""
    score = body_fit(
        attrs={"neckline": "v_neck", "fit": "tailored", "rise": "high_rise"},
        shape="Hourglass",
    )
    assert score >= 0.9
