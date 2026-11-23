"""Finance-side helpers for exception review and invoice release."""

from __future__ import annotations

from billing_engine import correct_mismatch, release_invoice, void_duplicate


def resolve_exception(run: dict, event_id: str, decision: str, reviewer: str) -> None:
    if decision == "correct_charge":
        correct_mismatch(run, event_id, reviewer)
    elif decision == "void_duplicate":
        void_duplicate(run, event_id, reviewer)
    else:
        raise ValueError("Unsupported Finance decision.")


def approve_invoice_release(run: dict, approver: str) -> None:
    release_invoice(run, approver)
