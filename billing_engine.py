"""Deterministic parcel billing validation logic for the demo application.

All rates and volume bands in this module are illustrative. Replace them with
Mitti Foods' signed contractual tariff before any real-world use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


DEMO_RATE_CARD: dict[str, Any] = {
    "name": "Mitti Foods – Illustrative Demo Tariff",
    "version": "DEMO-2026-01",
    "currency": "INR",
    "bands": [
        {"category": "Small", "min_volume_cm3": 0, "max_volume_cm3": 5000, "charge": "45.00"},
        {"category": "Medium", "min_volume_cm3": 5000, "max_volume_cm3": 15000, "charge": "60.00"},
        {"category": "Large", "min_volume_cm3": 15000, "max_volume_cm3": None, "charge": "75.00"},
    ],
}


def money(value: Any) -> Decimal:
    """Convert a value to Decimal without introducing float rounding noise."""
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid money value: {value!r}") from exc


def volume_cm3(length_cm: Any, width_cm: Any, height_cm: Any) -> int:
    """Calculate parcel volume in cubic centimetres."""
    dims = [Decimal(str(length_cm)), Decimal(str(width_cm)), Decimal(str(height_cm))]
    if any(d <= 0 for d in dims):
        raise ValueError("Parcel dimensions must be positive numbers.")
    return int(dims[0] * dims[1] * dims[2])


def price_for_volume(volume: int, rate_card: dict[str, Any] | None = None) -> tuple[str, Decimal]:
    """Return the category and charge from the supplied rate card."""
    card = rate_card or DEMO_RATE_CARD
    for band in card["bands"]:
        lower = int(band["min_volume_cm3"])
        upper = band["max_volume_cm3"]
        if volume >= lower and (upper is None or volume < int(upper)):
            return band["category"], money(band["charge"])
    raise ValueError(f"No rate-card band covers parcel volume {volume} cm³.")


def verify_billing_attempts(run: dict[str, Any], rate_card: dict[str, Any] | None = None) -> dict[str, int]:
    """Verify each billing attempt against the latest available warehouse scan.

    Duplicate attempts are detected by parcel ID. A parcel with no scan is held.
    A single valid attempt is matched or flagged as a category/charge mismatch.
    """
    card = rate_card or DEMO_RATE_CARD
    scans_by_parcel = {scan["parcel_id"]: scan for scan in run["scans"]}
    seen: set[str] = set()
    counts = {"matched": 0, "mismatch": 0, "missing_scan": 0, "duplicate": 0}

    for attempt in run["billing_attempts"]:
        parcel_id = attempt["parcel_id"]
        attempt["expected_category"] = None
        attempt["expected_charge"] = None
        attempt["variance"] = None
        attempt["reason"] = ""
        attempt["resolution_note"] = ""
        attempt["resolved_by"] = ""
        attempt["resolved_at"] = ""

        if parcel_id in seen:
            attempt["status"] = "duplicate"
            attempt["reason"] = "More than one billing attempt exists for this parcel ID."
            counts["duplicate"] += 1
            seen.add(parcel_id)
            continue

        seen.add(parcel_id)
        scan = scans_by_parcel.get(parcel_id)
        if scan is None:
            attempt["status"] = "missing_scan"
            attempt["reason"] = "No warehouse measurement is available for this parcel."
            counts["missing_scan"] += 1
            continue

        actual_volume = volume_cm3(scan["length_cm"], scan["width_cm"], scan["height_cm"])
        expected_category, expected_charge = price_for_volume(actual_volume, card)
        billed_amount = money(attempt["billed_amount"])
        variance = billed_amount - expected_charge

        attempt["expected_category"] = expected_category
        attempt["expected_charge"] = float(expected_charge)
        attempt["variance"] = float(variance)

        category_matches = attempt["billed_category"] == expected_category
        amount_matches = billed_amount == expected_charge
        if category_matches and amount_matches:
            attempt["status"] = "matched"
            attempt["reason"] = "Billed category and charge match the warehouse measurement and demo tariff."
            counts["matched"] += 1
        else:
            attempt["status"] = "mismatch"
            differences = []
            if not category_matches:
                differences.append(f"category billed as {attempt['billed_category']}, expected {expected_category}")
            if not amount_matches:
                differences.append(f"charge billed as ₹{billed_amount:.2f}, expected ₹{expected_charge:.2f}")
            attempt["reason"] = "; ".join(differences) + "."
            counts["mismatch"] += 1

    run["verified"] = True
    run["verification_counts"] = counts
    run["verified_at"] = datetime.now(timezone.utc).isoformat()
    return counts


def correct_mismatch(run: dict[str, Any], event_id: str, reviewer: str) -> None:
    """Apply the independently calculated expected category and charge."""
    attempt = _find_attempt(run, event_id)
    if attempt["status"] != "mismatch":
        raise ValueError("Only a verified mismatch can be corrected.")
    attempt["billed_category"] = attempt["expected_category"]
    attempt["billed_amount"] = float(money(attempt["expected_charge"]))
    attempt["status"] = "corrected"
    attempt["resolution_note"] = "Corrected to the charge calculated from the warehouse measurement and demo tariff."
    _stamp_resolution(attempt, reviewer)


def void_duplicate(run: dict[str, Any], event_id: str, reviewer: str) -> None:
    """Void a duplicate attempt while preserving its original evidence."""
    attempt = _find_attempt(run, event_id)
    if attempt["status"] != "duplicate":
        raise ValueError("Only a verified duplicate can be voided.")
    attempt["status"] = "voided"
    attempt["resolution_note"] = "Duplicate billing attempt voided; the first attempt remains the charge of record."
    _stamp_resolution(attempt, reviewer)


def _find_attempt(run: dict[str, Any], event_id: str) -> dict[str, Any]:
    for attempt in run["billing_attempts"]:
        if attempt["event_id"] == event_id:
            return attempt
    raise KeyError(f"Billing event not found: {event_id}")


def _stamp_resolution(attempt: dict[str, Any], reviewer: str) -> None:
    attempt["resolved_by"] = reviewer
    attempt["resolved_at"] = datetime.now(timezone.utc).isoformat()


def unresolved_attempts(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Return any attempt that still blocks invoice release."""
    cleared = {"matched", "corrected", "voided"}
    return [a for a in run["billing_attempts"] if a.get("status") not in cleared]


def release_invoice(run: dict[str, Any], approver: str) -> None:
    """Release only after every billing attempt is cleared."""
    if not run.get("verified"):
        raise ValueError("Verify the billing attempts before release.")
    pending = unresolved_attempts(run)
    if pending:
        raise ValueError(f"Cannot release invoice: {len(pending)} billing exceptions remain unresolved.")
    if not approver or not approver.strip():
        raise ValueError("An approver name is required.")
    if approver.strip() == run.get("created_by"):
        raise ValueError("The invoice creator cannot approve the same invoice run.")
    exception_reviewers = {
        a.get("resolved_by", "").strip()
        for a in run["billing_attempts"]
        if a.get("resolved_by", "").strip()
    }
    if approver.strip() in exception_reviewers:
        raise ValueError("The final approver must be different from the person who resolved billing exceptions.")
    run["released"] = True
    run["released_by"] = approver.strip()
    run["released_at"] = datetime.now(timezone.utc).isoformat()


def invoice_totals(run: dict[str, Any]) -> dict[str, float | int]:
    """Summarise the effective invoice total, excluding voided duplicate attempts."""
    included = [a for a in run["billing_attempts"] if a.get("status") != "voided"]
    total = sum((money(a["billed_amount"]) for a in included), Decimal("0.00"))
    return {"included_lines": len(included), "invoice_total": float(total)}


def csv_bytes(records: list[dict[str, Any]]) -> bytes:
    """Serialize records as UTF-8 CSV bytes for Streamlit downloads."""
    import csv
    import io

    if not records:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(records[0].keys()), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode("utf-8-sig")


def generate_billing_attempts(run: dict[str, Any], rate_card: dict[str, Any] | None = None) -> int:
    """Simulate ParcelPath billing, injecting controlled demo errors.

    For scanned parcels, normal charges follow the tariff. Eight selected
    attempts are deliberately misclassified. Five parcels without scans receive
    a Medium fallback charge, which the interceptor must hold. Two extra billing
    attempts are added for already-billed parcels to test duplicate detection.
    """
    import uuid

    from warehouse_simulator import CATEGORY_DIMENSIONS

    if run.get("billing_generated"):
        raise ValueError("Billing attempts have already been generated for this run.")

    card = rate_card or DEMO_RATE_CARD
    scans_by_parcel = {scan["parcel_id"]: scan for scan in run["scans"]}
    scanned_ids = sorted(scans_by_parcel.keys())
    misclassified_ids = set(scanned_ids[:8])
    parcels_by_id = {parcel["parcel_id"]: parcel for parcel in run["parcels"]}

    attempts: list[dict[str, Any]] = []
    primary_by_parcel: dict[str, dict[str, Any]] = {}
    for index, parcel in enumerate(run["parcels"], start=1):
        parcel_id = parcel["parcel_id"]
        scan = scans_by_parcel.get(parcel_id)
        if scan:
            volume = volume_cm3(scan["length_cm"], scan["width_cm"], scan["height_cm"])
            actual_category, actual_charge = price_for_volume(volume, card)
            billed_category, billed_amount = actual_category, actual_charge
            source = "WAREHOUSE_SCAN"
            if parcel_id in misclassified_ids:
                billed_category = "Small" if actual_category == "Large" else "Large"
                _, billed_amount = _charge_for_category(billed_category, card)
                source = "DELIBERATE_DEMO_MISCLASSIFICATION"
        else:
            billed_category = "Medium"
            _, billed_amount = _charge_for_category("Medium", card)
            source = "MANUAL_FALLBACK_NO_SCAN"

        attempt = {
            "event_id": f"BIL-{uuid.uuid4().hex[:10].upper()}",
            "invoice_line_id": f"LINE-{index:04d}",
            "parcel_id": parcel_id,
            "warehouse_id": parcel["warehouse_id"],
            "attempt_number": 1,
            "billed_category": billed_category,
            "billed_amount": float(money(billed_amount)),
            "currency": "INR",
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        attempts.append(attempt)
        primary_by_parcel[parcel_id] = attempt

    # Add two extra attempts against parcels whose original charges are valid.
    duplicate_candidates = [
        p["parcel_id"] for p in run["parcels"]
        if p["parcel_id"] in scans_by_parcel and p["parcel_id"] not in misclassified_ids
    ][:2]
    for duplicate_index, parcel_id in enumerate(duplicate_candidates, start=1):
        original = primary_by_parcel[parcel_id]
        duplicate = dict(original)
        duplicate.update({
            "event_id": f"DUP-{uuid.uuid4().hex[:10].upper()}",
            "invoice_line_id": f"DUP-LINE-{duplicate_index:03d}",
            "attempt_number": 2,
            "source": "DELIBERATE_DEMO_DUPLICATE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        })
        attempts.append(duplicate)

    run["billing_attempts"] = attempts
    run["billing_generated"] = True
    run["verified"] = False
    run["events"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "event": f"Billing simulator generated {len(attempts)} attempts, including deliberate demonstration exceptions.",
    })
    return len(attempts)


def _charge_for_category(category: str, rate_card: dict[str, Any]) -> tuple[str, Decimal]:
    for band in rate_card["bands"]:
        if band["category"] == category:
            return category, money(band["charge"])
    raise ValueError(f"Category {category!r} is missing from the rate card.")
