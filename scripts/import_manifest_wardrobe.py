"""Import clothing items from wardrobe manifest CSV into a user's wardrobe.

Safe, idempotent, and reusable utility.
- Resolves user ID dynamically from auth.users (never creates or assumes a user)
- Reuses existing data model and taxonomy helpers
- Preserves CSV image filenames/paths without substitution
- Respects database check constraints (formality <= 3) while storing manifest formality in metadata
- Skips already imported items to allow safe reruns
- Avoids exposing secrets or service role keys
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure backend modules can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.supabase import get_admin_supabase_client
from app.styling.rules import get_item_valid_occasions
from app.styling.taxonomy import normalize_manifest_item

WINTER_SUBCATEGORIES = {"sweater", "hoodie", "sweatshirt", "cardigan", "jacket", "coat", "blazer", "ethnic_jacket"}
SUMMER_SUBCATEGORIES = {"shorts", "tank", "sandals", "flip_flops", "crop_top"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wardrobe_importer")

DEFAULT_CSV_PATH = BACKEND_DIR / "tests" / "fixtures" / "test_wardrobe_manifest.csv"
TARGET_EMAIL = "kinshra35@gmail.com"


def resolve_user_id(client: Any, email: str) -> str:
    """Resolve auth user ID by email via Supabase admin API."""
    res = client.auth.admin.list_users()
    users = res if isinstance(res, list) else getattr(res, "users", [])
    target = [u for u in users if getattr(u, "email", None) and u.email.lower() == email.lower()]
    if not target:
        raise ValueError(f"User with email '{email}' was not found in auth.users. Cannot proceed.")
    return str(target[0].id)


def get_existing_wardrobe_keys(client: Any, user_id: str) -> set[str]:
    """Retrieve existing keys for user's wardrobe items to guarantee idempotency."""
    existing_keys: set[str] = set()
    try:
        res = client.from_("wardrobe_items").select("storage_path, image_url, metadata").eq("user_id", user_id).execute()
        for item in (res.data or []):
            sp = item.get("storage_path")
            if sp:
                existing_keys.add(sp)
                # Also index basename
                existing_keys.add(sp.split("/")[-1])
            img = item.get("image_url")
            if img:
                existing_keys.add(img)
                existing_keys.add(img.split("/")[-1])
            meta = item.get("metadata") or {}
            if isinstance(meta, dict):
                fn = meta.get("filename")
                if fn:
                    existing_keys.add(fn)
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


def import_manifest_to_wardrobe(
    csv_path: Path = DEFAULT_CSV_PATH,
    target_email: str = TARGET_EMAIL,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Import all clothing items in the CSV into the target user's wardrobe."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Wardrobe manifest CSV not found at: {csv_path}")

    client = get_admin_supabase_client()
    user_id = resolve_user_id(client, target_email)
    logger.info(f"Resolved user '{target_email}' to UUID: {user_id}")

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
            failed.append({"filename": "UNKNOWN", "name": name, "error": "Missing filename in CSV row"})
            continue

        storage_path = f"{user_id}/{filename}"

        # Idempotency check: avoid duplicate by filename or storage_path
        if filename in existing_keys or storage_path in existing_keys:
            skipped.append({
                "filename": filename,
                "name": name,
                "reason": "Item with matching filename or storage_path already exists in wardrobe",
            })
            continue

        # Normalize item using domain taxonomy
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

        # Formality handling: clamp to 0..3 for wardrobe_items check constraint
        raw_formality_str = row.get("formality")
        raw_formality = 1
        if raw_formality_str is not None and str(raw_formality_str).strip():
            try:
                raw_formality = int(raw_formality_str)
            except (ValueError, TypeError):
                raw_formality = 1
        db_formality = min(3, max(0, raw_formality))

        # Occasions derivation from rules engine
        occasions = sorted(list(get_item_valid_occasions(norm)))
        if not occasions:
            occasions = ["casual"]

        # Seasons derivation
        seasons = determine_seasons(sub_category, row.get("extra_attrs", ""), row.get("fabric", ""))

        # Style tags / vibes
        style_tags = norm.get("style_tags") or ["classic"]

        # Rich metadata preserving all CSV attributes
        metadata: dict[str, Any] = {
            "source_csv": str(csv_path.name),
            "filename": filename,
            "piece_id": piece_id,
            "name": name,
            "subtype": row.get("subtype") or None,
            "fabric": row.get("fabric") or None,
            "fit": fit,
            "length": length,
            "embellishment": row.get("embellishment") or None,
            "extra_attrs": row.get("extra_attrs") or None,
            "tag_mode": row.get("tag_mode") or None,
            "omit_fields": row.get("omit_fields") or None,
            "available": row.get("available") not in ("false", "0", "no", "False"),
            "is_available": row.get("available") not in ("false", "0", "no", "False"),
            "shoeless_user": row.get("shoeless_user") in (True, "yes", "true", "True"),
            "test_intent": test_intent,
            "manifest_formality": raw_formality,
            "role": norm.get("role"),
        }

        # Build wardrobe item record
        item_record = {
            "user_id": user_id,
            "image_url": filename,
            "storage_path": storage_path,
            "thumbnail_path": None,
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

        if dry_run:
            added.append({"filename": filename, "name": name, "category": cat, "slot": slot})
            existing_keys.add(filename)
            existing_keys.add(storage_path)
            continue

        try:
            insert_res = client.from_("wardrobe_items").insert(item_record).execute()
            if insert_res.data:
                added.append({
                    "id": insert_res.data[0]["id"],
                    "filename": filename,
                    "name": name,
                    "category": cat,
                    "slot": slot,
                })
                existing_keys.add(filename)
                existing_keys.add(storage_path)
            else:
                failed.append({"filename": filename, "name": name, "error": "Empty response from database insert"})
        except Exception as exc:
            logger.error(f"Error inserting row {filename}: {exc}")
            failed.append({"filename": filename, "name": name, "error": str(exc)})

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


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    try:
        report = import_manifest_to_wardrobe(dry_run=is_dry)
        print("\n" + "=" * 60)
        print("WARDROBE IMPORT REPORT")
        print("=" * 60)
        print(f"Target User: {report['target_email']} (ID: {report['user_id']})")
        print(f"Total CSV items: {report['total_csv_items']}")
        print(f"Added:   {report['added_count']}")
        print(f"Skipped: {report['skipped_count']}")
        print(f"Failed:  {report['failed_count']}")
        print("=" * 60)
        if report["skipped"]:
            print(f"\nSkipped {len(report['skipped'])} items (already exist):")
            for item in report["skipped"]:
                print(f"  - {item['filename']}: {item['name']}")
        if report["failed"]:
            print(f"\nFailed {len(report['failed'])} items:")
            for item in report["failed"]:
                print(f"  - {item['filename']}: {item['error']}")
        if report["added"]:
            print(f"\nAdded {len(report['added'])} items:")
            for item in report["added"]:
                print(f"  + [{item['slot']}/{item['category']}] {item['filename']}: {item['name']}")
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
