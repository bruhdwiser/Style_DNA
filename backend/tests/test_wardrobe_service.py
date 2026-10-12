"""Tests for wardrobe slot coverage and image sanitization/processing."""

import io
from PIL import Image
from app.styling.taxonomy import calculate_slot_coverage
from app.core.image_processing import sanitize_and_process_image, check_magic_bytes


def test_wardrobe_coverage_computation(sample_wardrobe):
    """Verify wardrobe slot counts and coverage status for capsule closet."""
    # Ensure sample wardrobe items have slot defined
    items_with_slots = [
        {**item, "slot": item.get("category", "top")}
        for item in sample_wardrobe
    ]
    coverage = calculate_slot_coverage(items_with_slots)

    core = coverage["core_coverage"]
    assert core["tops"] >= 3
    assert core["bottoms"] >= 2
    assert core["shoes"] >= 2
    assert core["layers"] >= 1
    assert coverage["total_items"] == len(sample_wardrobe)
    assert coverage["is_ready_for_outfits"] is True


def test_wardrobe_coverage_flags_missing_slots(make_item):
    """Verify that a wardrobe missing shoes and bottoms flags is_ready_for_outfits=False."""
    partial_wardrobe = [
        {**make_item("top", "t1"), "slot": "top"},
        {**make_item("top", "t2"), "slot": "top"},
    ]
    coverage = calculate_slot_coverage(partial_wardrobe)
    assert coverage["is_ready_for_outfits"] is False
    assert len(coverage["critical_missing"]) >= 1
    assert "shoes" in coverage["critical_missing"]


def test_image_processing_strips_metadata_and_creates_thumbnail():
    """Verify that Pillow sanitizes image, strips EXIF, and outputs clean JPEG."""
    # Create test RGB image in memory
    img = Image.new("RGB", (1200, 800), color=(100, 150, 200))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    raw_bytes = buffer.getvalue()

    # Magic byte check
    assert check_magic_bytes(raw_bytes) == "JPEG"

    processed = sanitize_and_process_image(raw_bytes)

    assert len(processed.display_bytes) > 0
    assert len(processed.thumbnail_bytes) > 0
    assert processed.format == "JPEG"
    assert processed.width <= 1600
    assert processed.height <= 1600

    # Thumbnail bounded to 320 max dimension
    thumb_img = Image.open(io.BytesIO(processed.thumbnail_bytes))
    assert max(thumb_img.size) <= 320
