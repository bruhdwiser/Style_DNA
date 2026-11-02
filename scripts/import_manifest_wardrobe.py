"""Import clothing items from wardrobe manifest CSV and image manifest into a user's wardrobe.

Production-grade, safe, idempotent, and reusable utility.
- Resolves target user UUID dynamically from auth.users (never creates or assumes a user ID).
- Verifies storage bucket availability before performing any database inserts.
- Imports ONLY rows where available is true and an unambiguous matching image file exists.
- Sanitizes images, strips EXIF, re-encodes to standard JPEG, and generates thumbnails using project conventions.
- Uploads images to the private 'wardrobe' storage bucket under {user_id}/{filename}.
- Respects database check constraints (formality <= 3) while preserving raw manifest formality in metadata.
- Guards against duplicate runs using stable CSV-derived keys (manifest filename, piece ID, storage path).
- Provides comprehensive reporting on added, skipped (unavailable, unmatched, already existing), and failed items.
- Never prints secrets, API keys, or service role credentials.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure backend modules can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.image_processing import sanitize_and_process_image
from app.core.supabase import get_admin_supabase_client
from app.styling.rules import get_item_valid_occasions
from app.styling.taxonomy import normalize_manifest_item

WINTER_SUBCATEGORIES = {"sweater", "hoodie", "sweatshirt", "cardigan", "jacket", "coat", "blazer", "ethnic_jacket"}
SUMMER_SUBCATEGORIES = {"shorts", "tank", "sandals", "flip_flops", "crop_top"}

STORAGE_BUCKET = "wardrobe"
DEFAULT_TARGET_EMAIL = "janmejayshukla2222@gmail.com"
DEFAULT_CSV_PATH = BACKEND_DIR / "tests" / "fixtures" / "test_wardrobe_manifest.csv"
DEFAULT_IMAGES_DIR = REPO_ROOT / "Outfits" / "Images manifest"

# 1-to-1 Explicit Image Mapping from test_wardrobe_manifest.csv filename to relative path in Outfits/Images manifest
MANIFEST_IMAGE_MAP: dict[str, Optional[str]] = {
    # Tops (14 images)
    "tshirt_01.jpg": "Tops/white_tee.png",
    "tshirt_02.jpg": "Tops/black_graphic_tee.png",
    "tshirt_03.jpg": "Tops/navy_striped_tee.png",  # available == False (must skip)
    "tank_01.jpg": "Tops/black_tank.png",
    "tank_02.jpg": "Tops/champagne_satin_cami.png",
    "crop_top_01.jpg": "Tops/blush_puff_sleeve_crop_top.png",
    "crop_top_02.jpg": "Tops/black_halter_crop.png",
    "shirt_formal_01.jpg": "Tops/white_button_down_shirt.png",
    "shirt_formal_02.jpg": "Tops/emerald_satin_shirt.png",
    "sweater_01.jpg": "Tops/beige_fineknit_sweater.png",
    "hoodie_01.jpg": "Tops/grey_hoodie.png",
    "kurti_01.jpg": "Tops/off_white_linen_kurti.png",
    "kurti_02.jpg": "Tops/eust_print_kurti.png",
    "kurti_03.jpg": "Tops/pastel_chikankaari_kurti.png",
    "blouse_01.jpg": None,  # No matching image in image manifest (must skip)

    # Bottoms and skirts (10 images)
    "jeans_01.jpg": "bottoms and skirts/dark_washed_straight_jeans.png",
    "jeans_02.jpg": "bottoms and skirts/light_washed_baggy_wide_leg_jeans.png",
    "jeans_03.jpg": "bottoms and skirts/medium_washed_flared_jeans.png",
    "trousers_casual_01.jpg": "bottoms and skirts/olive_cargo_pants.png",
    "skirt_01.jpg": "bottoms and skirts/pastel_floral_midi_skirt.png",
    "skirt_02.jpg": "bottoms and skirts/champagne_satin_midi_skirt.png",
    "shorts_01.jpg": "bottoms and skirts/beige_linen_bermuda_shorts.png",
    "palazzo_01.jpg": "bottoms and skirts/neutral_linen_pallazo_pants.png",
    "palazzo_02.jpg": "bottoms and skirts/indigo_block_print_pallazo_pants.png",
    "salwar_01.jpg": None,  # No matching image in image manifest (must skip)
    "lehenga_skirt_01.jpg": "bottoms and skirts/lehenga_skirt.png",

    # Dresses and sets (12 images)
    "midi_dress_01.jpg": "dresses and sets/pastel_greenaa and floral wrap midi dress.png",
    "midi_dress_02.jpg": "dresses and sets/olive_shirt_dress.png",
    "mini_dress_01.jpg": "dresses and sets/black_structured_shift_dress.png",
    "maxi_dress_01.jpg": "dresses and sets/rust and teal paisley maxi dress.png",
    "jumpsuit_01.jpg": "dresses and sets/navy wideleg crepe jumpsuit.png",
    "coord_set_01.jpg": "dresses and sets/bege linen co-ord set.png",
    "kurti_set_01.jpg": "dresses and sets/pastel blue chanderi kurti set.png",
    "kurti_set_02.jpg": "dresses and sets/emerald and gold velvet kurti set.png",
    "anarkali_01.jpg": "dresses and sets/pastel floral georgette anarkali.png",
    "lehenga_set_01.jpg": "dresses and sets/red and gold zari brocade lehenga set.png",
    "saree_01.jpg": "dresses and sets/WINE AND GOLD BANARASI SILK SAREE.png",
    "saree_02.jpg": "dresses and sets/teal and ivory handloom cotton saree.png",

    # Layers (6 images)
    "jacket_01.jpg": "layers/classic blue denim jacket.png",
    "jacket_02.jpg": "layers/black faux lether biker jacket.png",  # available == False (must skip)
    "cardigan_01.jpg": "layers/cream fine knit cardingsn.png",
    "cardigan_02.jpg": "layers/grey chunky oversized cradingsn.png",
    "shrug_01.jpg": "layers/cream crochet shrug.png",
    "ethnic_jacket_01.jpg": "layers/navy and gold embroided ethnic jacket.png",

    # Footwear (8 images)
    "sneakers_01.jpg": "footwear/white low top canvas sneaker s.png",
    "sneakers_02.jpg": "footwear/chunky colour block sneakers.png",
    "chappals_01.jpg": "footwear/tan braided kolhapuri chappal.png",
    "chappals_02.jpg": "footwear/gold embellished flats.png",
    "mules_01.jpg": "footwear/black square toe mules.png",
    "heels_01.jpg": "footwear/nude block heel pumps.png",
    "jutti_01.jpg": "footwear/gold zari ambroided jutti.png",
    "jutti_02.jpg": "footwear/plain tan mule jutti.png",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wardrobe_importer")


def resolve_user_id(client: Any, email: str) -> str:
    """Resolve auth user ID by email via Supabase admin API without assuming ID or creating a user."""
    res = client.auth.admin.list_users()
    users = res if isinstance(res, list) else getattr(res, "users", [])
    target = [u for u in users if getattr(u, "email", None) and u.email.lower() == email.lower()]
    if not target:
        raise ValueError(f"User with email '{email}' was not found in auth.users. Cannot proceed.")
    return str(target[0].id)


def verify_storage_bucket(client: Any) -> None:
    """Ensure the private wardrobe storage bucket is reachable."""
    try:
        buckets = client.storage.list_buckets()
        bucket_names = [b.name if hasattr(b, "name") else b.get("name") for b in buckets]
        if STORAGE_BUCKET not in bucket_names:
            raise RuntimeError(f"Required storage bucket '{STORAGE_BUCKET}' does not exist in Supabase.")
    except Exception as exc:
        raise RuntimeError(f"Unable to access Supabase Storage: {exc}")


def get_existing_wardrobe_keys(client: Any, user_id: str) -> set[str]:
    """Retrieve existing keys for user's wardrobe items to guarantee idempotency across reruns."""
    existing_keys: set[str] = set()
    try:
        res = client.from_("wardrobe_items").select("storage_path, thumbnail_path, image_url, metadata").eq("user_id", user_id).execute()
        for item in (res.data or []):
            sp = item.get("storage_path")
            if sp:
                existing_keys.add(sp)
                existing_keys.add(sp.split("/")[-1])
            img = item.get("image_url")
            if img:
                existing_keys.add(img)
                existing_keys.add(img.split("/")[-1])
            meta = item.get("metadata") or {}
            if isinstance(meta, dict):
                for k in ("manifest_filename", "filename", "manifest_piece_id", "piece_id"):
                    val = meta.get(k)
                    if val:
                        existing_keys.add(str(val))
    except Exception as exc:
        logger.error(f"Failed to query existing wardrobe items: {exc}")
        raise
    return existing_keys


def determine_seasons(sub_category: str, extra_attrs: str, fabric: str) -> list[str]:
    """Determine seasons list based on item subtype, knit gauge, and fabric."""
    sub_norm = (sub_category or "").strip().lower()
    extra_norm = (extra_attrs or "").strip().lower()
    fabric_norm = (fabric or "").strip().lower()

    if sub_norm in WINTER_SUBCATEGORIES or "knit_gauge" in extra_norm or fabric_norm in ("wool", "fleece"):
        return ["winter", "all_season"]
    if sub_norm in SUMMER_SUBCATEGORIES or fabric_norm in ("linen", "chiffon"):
        return ["summer", "all_season"]
    return ["all_season"]


def import_manifest_wardrobe(
    target_email: str = DEFAULT_TARGET_EMAIL,
    csv_path: Path = DEFAULT_CSV_PATH,
    images_dir: Path = DEFAULT_IMAGES_DIR,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Import available clothing items with matched images into target user's wardrobe."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Wardrobe manifest CSV not found at: {csv_path}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Wardrobe image directory not found at: {images_dir}")

    client = get_admin_supabase_client()
    user_id = resolve_user_id(client, target_email)
    logger.info(f"Resolved user '{target_email}' to UUID: {user_id}")

    verify_storage_bucket(client)
    logger.info(f"Verified Supabase Storage bucket '{STORAGE_BUCKET}' is reachable.")

    existing_keys = get_existing_wardrobe_keys(client, user_id)
    logger.info(f"Found {len(existing_keys)} existing path/filename keys in user wardrobe.")

    rows: list[dict[str, str]] = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"Read {len(rows)} clothing items from {csv_path.name}")

    added: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for row in rows:
        filename = (row.get("filename") or "").strip()
        piece_id = (row.get("piece_id") or "").strip()
        name = (row.get("name") or piece_id).strip()

        if not filename:
            failed.append({
                "filename": "UNKNOWN",
                "piece_id": piece_id,
                "name": name,
                "error": "Missing filename in CSV row",
            })
            continue

        # Rule 1: Check availability — import ONLY rows where available is true
        is_available = row.get("available") not in ("false", "0", "no", "False")
        if not is_available:
            skipped.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "reason": "Unavailable (marked available=false in manifest)",
            })
            continue

        # Rule 2: Check matching image — must have a clear, unambiguous matching image
        matched_rel_path = MANIFEST_IMAGE_MAP.get(filename)
        if not matched_rel_path:
            skipped.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "reason": "Unmatched (no corresponding image found in image manifest)",
            })
            continue

        local_img_path = images_dir / matched_rel_path
        if not local_img_path.exists():
            skipped.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "reason": f"Image file missing on disk: {matched_rel_path}",
            })
            continue

        # Rule 3: Idempotency check — avoid duplicates using stable filename or storage_path
        stem = Path(filename).stem
        storage_path = f"{user_id}/{stem}.jpg"
        thumb_path = f"{user_id}/{stem}_thumb.jpg"

        if (
            filename in existing_keys
            or storage_path in existing_keys
            or piece_id in existing_keys
            or f"{stem}.jpg" in existing_keys
        ):
            skipped.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "reason": "Already exists in user's wardrobe",
            })
            continue

        # Normalize taxonomy
        norm = normalize_manifest_item(row)
        cat = norm.get("category", "top")
        slot = norm.get("slot", "top")
        sub_category = norm.get("sub_category") or piece_id
        primary_color = norm.get("primary_color") or "black"
        color_tags = norm.get("color_tags") or [primary_color]
        fit = row.get("fit") or None
        length = row.get("length") or None
        pattern = norm.get("pattern", "solid")
        test_intent = row.get("test_intent") or ""

        # Formality clamping (0..3 for check constraint)
        raw_formality_str = row.get("formality")
        raw_formality = 1
        if raw_formality_str is not None and str(raw_formality_str).strip():
            try:
                raw_formality = int(raw_formality_str)
            except (ValueError, TypeError):
                raw_formality = 1
        db_formality = min(3, max(0, raw_formality))

        # Occasions and seasons
        occasions = sorted(list(get_item_valid_occasions(norm)))
        if not occasions:
            occasions = ["casual"]
        seasons = determine_seasons(sub_category, row.get("extra_attrs", ""), row.get("fabric", ""))
        style_tags = norm.get("style_tags") or ["classic"]

        if dry_run:
            added.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "category": cat,
                "slot": slot,
                "image_file": str(matched_rel_path),
                "storage_path": storage_path,
            })
            existing_keys.add(filename)
            existing_keys.add(storage_path)
            continue

        # Image Processing & Upload
        try:
            with open(local_img_path, "rb") as img_file:
                raw_bytes = img_file.read()

            processed = sanitize_and_process_image(raw_bytes)

            # Upload sanitized display image
            client.storage.from_(STORAGE_BUCKET).upload(
                storage_path,
                processed.display_bytes,
                {"content-type": "image/jpeg", "upsert": "true"},
            )

            # Upload thumbnail
            client.storage.from_(STORAGE_BUCKET).upload(
                thumb_path,
                processed.thumbnail_bytes,
                {"content-type": "image/jpeg", "upsert": "true"},
            )

            # Complete metadata
            metadata: dict[str, Any] = {
                "source_csv": str(csv_path.name),
                "manifest_filename": filename,
                "manifest_piece_id": piece_id,
                "manifest_name": name,
                "manifest_image_path": str(matched_rel_path),
                "manifest_formality": raw_formality,
                "available": True,
                "is_available": True,
                "subtype": row.get("subtype") or None,
                "fabric": row.get("fabric") or None,
                "fit": fit,
                "length": length,
                "embellishment": row.get("embellishment") or None,
                "extra_attrs": row.get("extra_attrs") or None,
                "tag_mode": row.get("tag_mode") or None,
                "omit_fields": row.get("omit_fields") or None,
                "shoeless_user": row.get("shoeless_user") in (True, "yes", "true", "True"),
                "test_intent": test_intent,
                "role": norm.get("role"),
                "width": processed.width,
                "height": processed.height,
                "byte_size": processed.byte_size,
                "display_format": processed.format,
                "mime_type": processed.mime_type,
                "metadata_stripped": True,
            }

            item_record = {
                "user_id": user_id,
                "image_url": storage_path,
                "storage_path": storage_path,
                "thumbnail_path": thumb_path,
                "category": cat,
                "slot": slot,
                "sub_category": sub_category,
                "primary_color": primary_color,
                "color_tags": color_tags,
                "fit": fit,
                "length": length,
                "formality": db_formality,
                "occasions": occasions,
                "seasons": seasons,
                "style_tags": style_tags,
                "pattern": pattern,
                "notes": test_intent or None,
                "needs_review": False,
                "metadata": metadata,
            }

            insert_res = client.from_("wardrobe_items").insert(item_record).execute()
            if insert_res.data:
                added.append({
                    "id": insert_res.data[0]["id"],
                    "filename": filename,
                    "piece_id": piece_id,
                    "name": name,
                    "category": cat,
                    "slot": slot,
                    "storage_path": storage_path,
                })
                existing_keys.add(filename)
                existing_keys.add(storage_path)
            else:
                failed.append({
                    "filename": filename,
                    "piece_id": piece_id,
                    "name": name,
                    "error": "Empty response from database insert",
                })
        except Exception as exc:
            logger.error(f"Error processing/uploading {filename}: {exc}")
            failed.append({
                "filename": filename,
                "piece_id": piece_id,
                "name": name,
                "error": str(exc),
            })

    return {
        "target_email": target_email,
        "user_id": user_id,
        "total_csv_items": len(rows),
        "added_count": len(added),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "added": added,
        "skipped": skipped,
        "failed": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manifest clothing items to Supabase wardrobe.")
    parser.add_argument("--email", default=DEFAULT_TARGET_EMAIL, help=f"Target user email (default: {DEFAULT_TARGET_EMAIL})")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to wardrobe manifest CSV")
    parser.add_argument("--images-dir", default=str(DEFAULT_IMAGES_DIR), help="Path to wardrobe images manifest directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without uploading or inserting")

    args = parser.parse_args()

    try:
        report = import_manifest_wardrobe(
            target_email=args.email,
            csv_path=Path(args.csv),
            images_dir=Path(args.images_dir),
            dry_run=args.dry_run,
        )

        mode_str = " (DRY RUN)" if args.dry_run else ""
        print("\n" + "=" * 70)
        print(f"WARDROBE IMPORT REPORT{mode_str}")
        print("=" * 70)
        print(f"Target User:     {report['target_email']} (UUID: {report['user_id']})")
        print(f"Total CSV items: {report['total_csv_items']}")
        print(f"Added items:     {report['added_count']}")
        print(f"Skipped items:   {report['skipped_count']}")
        print(f"Failed items:    {report['failed_count']}")
        print("=" * 70)

        # Categorize skipped items for clear breakdown
        skipped_unavail = [i for i in report["skipped"] if "available=false" in i.get("reason", "").lower()]
        skipped_unmatched = [i for i in report["skipped"] if "unmatched" in i.get("reason", "").lower()]
        skipped_existing = [i for i in report["skipped"] if "already exists" in i.get("reason", "").lower()]

        if skipped_unavail:
            print(f"\nSkipped {len(skipped_unavail)} Unavailable Items (available=false):")
            for item in skipped_unavail:
                print(f"  - [{item['piece_id']}] {item['filename']}: {item['name']}")

        if skipped_unmatched:
            print(f"\nSkipped {len(skipped_unmatched)} Unmatched Items (missing image in manifest):")
            for item in skipped_unmatched:
                print(f"  - [{item['piece_id']}] {item['filename']}: {item['name']}")

        if skipped_existing:
            print(f"\nSkipped {len(skipped_existing)} Already Existing Items:")
            for item in skipped_existing:
                print(f"  - [{item['piece_id']}] {item['filename']}: {item['name']}")

        if report["failed"]:
            print(f"\nFailed {len(report['failed'])} Items:")
            for item in report["failed"]:
                print(f"  - [{item['piece_id']}] {item['filename']}: {item['error']}")

        if report["added"]:
            print(f"\nSuccessfully Added {len(report['added'])} Items:")
            for item in report["added"]:
                print(f"  + [{item['slot']}/{item['category']}] {item['filename']}: {item['name']}")

    except Exception as err:
        print(f"\nERROR: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
