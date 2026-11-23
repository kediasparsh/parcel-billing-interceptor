"""Creates realistic but fictional warehouse scan events for demonstration."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


CATEGORY_DIMENSIONS = {
    "Small": (20, 10, 10),       # 2,000 cm³
    "Medium": (25, 20, 15),     # 7,500 cm³
    "Large": (40, 30, 20),      # 24,000 cm³
}


def _iso(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def create_warehouse_run(run_id: str, created_by: str, parcel_count: int = 100, scan_count: int = 95, seed: int = 20261123) -> dict[str, Any]:
    """Create parcel master records and scanner events.

    Five parcels intentionally have no initial scan. Their underlying demo
    dimensions are retained privately in the run so a re-scan can be simulated.
    """
    if parcel_count < 1 or not (0 <= scan_count <= parcel_count):
        raise ValueError("Invalid parcel or scan count.")

    rng = random.Random(seed)
    categories = ["Small", "Medium", "Large"]
    parcels: list[dict[str, Any]] = []
    for index in range(1, parcel_count + 1):
        # Ensure missing-scan examples have non-Medium sizes so re-scan reveals
        # an actionable billing mismatch in this controlled demonstration.
        if index > scan_count:
            category = "Small" if index % 2 == 0 else "Large"
        else:
            category = rng.choice(categories)
        length, width, height = CATEGORY_DIMENSIONS[category]
        parcels.append({
            "parcel_id": f"PKG-{index:04d}",
            "warehouse_id": f"WH-{rng.randint(1, 3):02d}",
            "scanner_id": None,
            "actual_category_demo": category,
            "actual_length_cm": length,
            "actual_width_cm": width,
            "actual_height_cm": height,
            "actual_weight_kg": round(rng.uniform(0.2, 4.8), 2),
            "created_at": _iso(rng.randint(1, 180)),
        })

    scanned_indices = set(rng.sample(range(parcel_count), scan_count))
    scans: list[dict[str, Any]] = []
    for index, parcel in enumerate(parcels):
        if index not in scanned_indices:
            continue
        scans.append(_make_scan(parcel, scan_number=len(scans) + 1, rng=rng))

    return {
        "run_id": run_id,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parcels": parcels,
        "scans": scans,
        "billing_attempts": [],
        "billing_generated": False,
        "verified": False,
        "verification_counts": {},
        "released": False,
        "events": [
            {"time": datetime.now(timezone.utc).isoformat(), "event": f"Warehouse simulation created: {parcel_count} parcels, {scan_count} initial scans."}
        ],
    }


def _make_scan(parcel: dict[str, Any], scan_number: int, rng: random.Random | None = None) -> dict[str, Any]:
    rng = rng or random.Random()
    return {
        "scan_id": f"SCN-{uuid.uuid4().hex[:10].upper()}",
        "parcel_id": parcel["parcel_id"],
        "warehouse_id": parcel["warehouse_id"],
        "scanner_id": f"DIM-{parcel['warehouse_id']}-01",
        "length_cm": parcel["actual_length_cm"],
        "width_cm": parcel["actual_width_cm"],
        "height_cm": parcel["actual_height_cm"],
        "weight_kg": parcel["actual_weight_kg"],
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scan_number": scan_number,
    }


def rescan_missing_parcels(run: dict[str, Any]) -> int:
    """Simulate re-scanning parcels that had no initial measurement event."""
    scanned = {scan["parcel_id"] for scan in run["scans"]}
    missing = [p for p in run["parcels"] if p["parcel_id"] not in scanned]
    for parcel in missing:
        run["scans"].append(_make_scan(parcel, scan_number=len(run["scans"]) + 1))
    if missing:
        run["verified"] = False
        run["events"].append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": f"Operations re-scanned {len(missing)} parcels that previously had no measurement record.",
        })
    return len(missing)


def scan_table(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Return scanner data without exposing hidden dimensions for unscanned parcels."""
    return [
        {k: scan[k] for k in ("scan_id", "parcel_id", "warehouse_id", "scanner_id", "length_cm", "width_cm", "height_cm", "weight_kg", "scanned_at")}
        for scan in run["scans"]
    ]
