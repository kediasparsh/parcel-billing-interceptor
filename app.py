from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from billing_engine import (
    DEMO_RATE_CARD,
    csv_bytes,
    generate_billing_attempts,
    invoice_totals,
    unresolved_attempts,
    verify_billing_attempts,
)
from finance import approve_invoice_release, resolve_exception
from warehouse_simulator import create_warehouse_run, rescan_missing_parcels, scan_table


st.set_page_config(
    page_title="ParcelPath Billing Interceptor",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Visual styling -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --navy:#171638; --purple:#6C4CF1; --purple2:#8A72FF; --muted:#6D6B83; --line:#E8E6F2; --bg:#F7F7FC; }
.stApp { background:var(--bg); color:var(--navy); font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(247,247,252,0.92); }
.block-container { max-width:1450px; padding-top:1.5rem; padding-bottom:3rem; }
h1,h2,h3,h4 { font-family:'Manrope',sans-serif !important; color:var(--navy) !important; letter-spacing:-0.035em; }
[data-testid="stSidebar"] { background:#F0EEFA; border-right:1px solid #E5E1F3; }
[data-testid="stSidebar"] * { color:var(--navy); }
div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 3px 12px rgba(27,22,72,0.035); }
div[data-testid="stMetricLabel"] { color:var(--muted); font-weight:600; }
div[data-testid="stMetricValue"] { color:var(--navy); font-family:'Manrope',sans-serif; }
.stButton > button, .stDownloadButton > button { border-radius:11px; min-height:2.7rem; font-weight:700; border:1px solid #DCD7F3; }
.stButton > button[kind="primary"] { background:var(--purple); border-color:var(--purple); color:white; }
.stButton > button:hover { border-color:var(--purple); color:var(--purple); }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
div[data-testid="stExpander"] { background:white; border:1px solid var(--line); border-radius:12px; }
.hero { background:linear-gradient(112deg,#171638 0%,#2C2466 58%,#6C4CF1 100%); padding:30px 34px; border-radius:22px; color:white; margin:0 0 24px 0; box-shadow:0 12px 28px rgba(46,35,111,.13); }
.hero h1 { color:white !important; font-size:2.35rem; margin:0 0 8px 0; }
.hero p { color:#E7E4FF; margin:0; font-size:1rem; max-width:850px; }
.hero .eyebrow { color:#CFC7FF; font-size:.75rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; margin-bottom:12px; }
.section-label { color:var(--purple); font-size:.73rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:12px 0 8px 0; }
.info-card { background:white; border:1px solid var(--line); border-radius:16px; padding:18px 20px; height:100%; }
.info-card h3 { font-size:1.05rem; margin:0 0 8px 0; }
.info-card p { color:var(--muted); font-size:.9rem; margin:0; }
.pill { display:inline-block; padding:5px 10px; border-radius:999px; font-size:.72rem; font-weight:800; background:#EEEAFE; color:#5C43D6; }
.small-muted { color:var(--muted); font-size:.82rem; }
.step { background:white; border:1px solid var(--line); border-radius:14px; padding:14px; min-height:100px; }
.step b { display:block; color:var(--navy); margin-bottom:5px; }
.step span { color:var(--muted); font-size:.82rem; }
[data-testid="stAlert"] { border-radius:12px; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- Session state ------------------------------
if "run" not in st.session_state:
    st.session_state.run = None
if "page" not in st.session_state:
    st.session_state.page = "Overview"


def money_inr(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"₹{float(value):,.2f}"


def page_title(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='section-label'>PARCELPATH × MITTI FOODS</div><h1 style='margin:0'>{title}</h1><p class='small-muted' style='margin-top:6px'>{subtitle}</p>", unsafe_allow_html=True)


def add_event(run: dict, message: str) -> None:
    run["events"].append({"time": datetime.now().astimezone().isoformat(timespec="seconds"), "event": message})


def safe_dataframe(records: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns or [])
    frame = pd.DataFrame(records)
    if columns:
        available = [c for c in columns if c in frame.columns]
        frame = frame[available]
    return frame


def status_label(value: str) -> str:
    return {
        "matched": "Matched",
        "mismatch": "Charge mismatch",
        "missing_scan": "Missing scan",
        "duplicate": "Duplicate attempt",
        "corrected": "Corrected",
        "voided": "Voided",
    }.get(value, value.replace("_", " ").title())


# -------------------------------- Sidebar ----------------------------------
with st.sidebar:
    st.markdown("# 📦 ParcelPath")
    st.markdown("**Billing Interceptor**")
    st.caption("Mitti Foods · Demonstration environment")
    st.divider()
    selected_page = st.radio(
        "WORKSPACE",
        ["Overview", "01 · Warehouse", "02 · Billing", "03 · Interception", "04 · Finance"],
        label_visibility="visible",
    )
    st.session_state.page = selected_page
    st.divider()
    demo_role = st.selectbox("DEMO VIEW", ["Operations", "Finance"])
    st.caption("Role switching is simulated for this public demonstration. It is not secure authentication.")
    st.divider()
    if st.session_state.run:
        run = st.session_state.run
        st.markdown("**CURRENT RUN**")
        st.code(run["run_id"], language=None)
        st.caption(f"{len(run['parcels'])} parcels · {len(run['scans'])} scans · {len(run['billing_attempts'])} billing attempts")
        if st.button("Reset demonstration", use_container_width=True):
            st.session_state.run = None
            st.rerun()
    st.markdown("---")
    st.caption("Illustrative data and tariff only. Not connected to ParcelPath or Mitti systems.")

page = selected_page
run = st.session_state.run

# -------------------------------- Overview ---------------------------------
if page == "Overview":
    st.markdown("""
    <div class='hero'>
      <div class='eyebrow'>Warehouse-to-invoice control</div>
      <h1>Catch the billing error before it reaches the customer.</h1>
      <p>Independently verify every parcel charge against the warehouse measurement, hold exceptions, and release the invoice only after Finance review.</p>
    </div>
    """, unsafe_allow_html=True)

    if run:
        attempts = run["billing_attempts"]
        matched = sum(a.get("status") == "matched" for a in attempts)
        held = sum(a.get("status") in {"mismatch", "missing_scan", "duplicate"} for a in attempts)
        unresolved = len(unresolved_attempts(run)) if run.get("verified") else 0
        cols = st.columns(4)
        cols[0].metric("Parcels", len(run["parcels"]))
        cols[1].metric("Warehouse scans", len(run["scans"]))
        cols[2].metric("Billing attempts", len(attempts))
        cols[3].metric("Open holds", unresolved if run.get("verified") else "Not verified")
    else:
        cols = st.columns(4)
        cols[0].metric("Parcels", "—", help="Run the warehouse simulation to begin.")
        cols[1].metric("Scanner events", "—")
        cols[2].metric("Billing attempts", "—")
        cols[3].metric("Charges intercepted", "—")

    st.markdown("<div class='section-label'>HOW THE CONTROL WORKS</div>", unsafe_allow_html=True)
    steps = st.columns(4)
    step_data = [
        ("01 · Measure", "Warehouse records the parcel dimensions and weight."),
        ("02 · Bill", "ParcelPath generates a proposed charge."),
        ("03 · Verify", "The interceptor checks category and amount independently."),
        ("04 · Approve", "Finance resolves exceptions before release."),
    ]
    for col, (title, desc) in zip(steps, step_data):
        with col:
            st.markdown(f"<div class='step'><b>{title}</b><span>{desc}</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label'>START THE DEMONSTRATION</div>", unsafe_allow_html=True)
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### Run a simulated warehouse shift")
        st.write("Generate 100 fictional parcels, 95 initial scanner records, 102 billing attempts and controlled billing errors. Then follow the exceptions through Finance review.")
        if st.button("▶  Start 100-parcel simulation", type="primary", use_container_width=True, disabled=run is not None):
            new_id = f"PP-{datetime.now().strftime('%y%m%d-%H%M%S')}"
            st.session_state.run = create_warehouse_run(new_id, created_by="Operations User")
            st.success("Warehouse simulation created. Continue to 01 · Warehouse.")
            st.rerun()
        if run is not None:
            st.success(f"Run {run['run_id']} is active. Continue through the four stages using the left menu.")
    with right:
        st.markdown("### What this demonstration proves")
        st.markdown("- A parcel is measured independently of billing.\n- Wrong, duplicate or unsupported charges are held.\n- Missing measurements can be re-scanned.\n- Finance must resolve all holds before release.")

    st.info("Demo tariff: Small ₹45, Medium ₹60 and Large ₹75 using volume bands. These prices are fictional and must be replaced with the signed contract rules in a real deployment.")

# --------------------------- Warehouse simulation -------------------------
elif page == "01 · Warehouse":
    page_title("Warehouse scanner", "Simulate parcels moving through a dimensioning station.")
    if run is None:
        st.warning("Start a new demonstration from the Overview page first.")
    else:
        scanned_ids = {s["parcel_id"] for s in run["scans"]}
        missing_count = len(run["parcels"]) - len(scanned_ids)
        c1, c2, c3 = st.columns(3)
        c1.metric("Parcels received", len(run["parcels"]))
        c2.metric("Successful scans", len(run["scans"]))
        c3.metric("Awaiting re-scan", missing_count)
        st.markdown("### Scanner event log")
        st.caption("Every scanner event records a unique parcel ID, warehouse, scanner, dimensions, weight and timestamp.")
        st.dataframe(safe_dataframe(scan_table(run)), use_container_width=True, hide_index=True, height=360)
        st.download_button("Download scanner records (CSV)", csv_bytes(scan_table(run)), f"{run['run_id']}_scanner_records.csv", "text/csv")
        if missing_count:
            st.markdown("### Missing measurement records")
            st.warning(f"{missing_count} parcels have no measurement record. Billing must not be accepted for these parcels until a valid measurement is captured.")
            if demo_role == "Operations":
                if st.button("↻  Re-scan missing parcels", type="primary"):
                    count = rescan_missing_parcels(run)
                    add_event(run, f"Operations re-scan completed for {count} missing parcel measurements.")
                    st.success(f"Captured {count} additional measurement records. Go to Interception and verify charges again.")
                    st.rerun()
            else:
                st.info("Switch the demo view to Operations to perform the re-scan.")
        else:
            st.success("All parcels now have a measurement record.")
        with st.expander("What does a warehouse scan contain?"):
            st.write("Parcel ID, warehouse ID, scanner ID, length, width, height, weight and scan timestamp. In a live system, these fields would arrive from the warehouse dimensioning equipment.")

# -------------------------------- Billing ----------------------------------
elif page == "02 · Billing":
    page_title("ParcelPath billing engine", "Generate a proposed charge for each parcel, including controlled errors for testing.")
    if run is None:
        st.warning("Start a new demonstration from the Overview page first.")
    else:
        if not run["billing_generated"]:
            st.markdown("### Illustrative contract tariff")
            tariff_df = pd.DataFrame([
                {"Category": b["category"], "Volume from (cm³)": b["min_volume_cm3"], "Volume below (cm³)": b["max_volume_cm3"] or "No upper limit", "Charge": f"₹{float(b['charge']):.2f}"}
                for b in DEMO_RATE_CARD["bands"]
            ])
            st.dataframe(tariff_df, use_container_width=True, hide_index=True)
            st.info("This tariff is fictional for demonstration. The actual contract may use different size, weight, zone or service rules.")
            if demo_role == "Operations":
                if st.button("Generate ParcelPath charges", type="primary"):
                    count = generate_billing_attempts(run)
                    add_event(run, f"Billing system generated {count} billing attempts.")
                    st.success(f"Generated {count} billing attempts. Continue to Interception.")
                    st.rerun()
            else:
                st.info("Switch the demo view to Operations to generate billing attempts.")
        else:
            st.success(f"Billing system has generated {len(run['billing_attempts'])} attempts for {len(run['parcels'])} unique parcels.")
            display_cols = ["event_id", "invoice_line_id", "parcel_id", "warehouse_id", "attempt_number", "billed_category", "billed_amount", "source"]
            st.dataframe(safe_dataframe(run["billing_attempts"], display_cols), use_container_width=True, hide_index=True, height=400)
            st.download_button("Download billing attempts (CSV)", csv_bytes(run["billing_attempts"]), f"{run['run_id']}_billing_attempts.csv", "text/csv")
            st.caption("The simulation deliberately introduces eight wrong parcel classifications, five charges without a scan record and two duplicate attempts. These are controlled test cases, not actual customer data.")

# ------------------------------ Interception -------------------------------
elif page == "03 · Interception":
    page_title("Interception centre", "Compare every billing attempt with the warehouse measurement and stop unsupported charges.")
    if run is None or not run["billing_generated"]:
        st.warning("Generate ParcelPath billing attempts before running verification.")
    else:
        if not run.get("verified"):
            st.markdown("### Independent verification")
            st.write("The interceptor uses the scanner record and the demo rate card to calculate the expected category and charge. It does not trust the category supplied by the billing system.")
            if st.button("Verify all billing attempts", type="primary"):
                counts = verify_billing_attempts(run)
                add_event(run, "Independent billing verification completed.")
                st.success("Verification completed.")
                st.rerun()
        if run.get("verified"):
            counts = run["verification_counts"]
            attempts = run["billing_attempts"]
            summary = st.columns(4)
            summary[0].metric("Matched", counts.get("matched", 0))
            summary[1].metric("Charge mismatches", counts.get("mismatch", 0))
            summary[2].metric("Missing scans", counts.get("missing_scan", 0))
            summary[3].metric("Duplicates", counts.get("duplicate", 0))
            st.markdown("### Billing attempt results")
            display = []
            for a in attempts:
                display.append({
                    "Event": a["event_id"],
                    "Parcel": a["parcel_id"],
                    "Warehouse": a["warehouse_id"],
                    "Billed category": a["billed_category"],
                    "Expected category": a.get("expected_category") or "—",
                    "Billed ₹": a["billed_amount"],
                    "Expected ₹": a.get("expected_charge") if a.get("expected_charge") is not None else "—",
                    "Status": status_label(a["status"]),
                })
            st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True, height=430)
            st.download_button("Download verification report (CSV)", csv_bytes(display), f"{run['run_id']}_verification.csv", "text/csv")
            pending = unresolved_attempts(run)
            if pending:
                st.warning(f"{len(pending)} billing attempts are on hold. Resolve all exceptions before invoice release.")
            else:
                st.success("All billing attempts have been cleared. Finance can proceed to invoice approval.")
            by_warehouse: dict[str, int] = {}
            for a in attempts:
                if a["status"] in {"mismatch", "missing_scan", "duplicate"}:
                    by_warehouse[a["warehouse_id"]] = by_warehouse.get(a["warehouse_id"], 0) + 1
            if by_warehouse:
                st.markdown("### Where are exceptions appearing?")
                warehouse_df = pd.DataFrame([{"Warehouse": k, "Open exceptions": v} for k, v in sorted(by_warehouse.items())])
                st.bar_chart(warehouse_df.set_index("Warehouse"), color="#6C4CF1")

# -------------------------------- Finance ---------------------------------
elif page == "04 · Finance":
    page_title("Finance review & invoice release", "Resolve exceptions, record the decision and release only a fully cleared invoice.")
    if demo_role != "Finance":
        st.warning("This screen is reserved for the Finance demo role. Switch DEMO VIEW to Finance in the sidebar.")
    elif run is None or not run.get("verified"):
        st.warning("Run the warehouse and billing simulation, then verify charges before Finance review.")
    else:
        reviewer = st.text_input("Finance reviewer name", value="Finance Reviewer")
        approver = st.text_input("Final invoice approver name", value="Finance Approver")
        attempts = run["billing_attempts"]
        pending = unresolved_attempts(run)
        counts = {
            "mismatch": sum(a["status"] == "mismatch" for a in attempts),
            "missing_scan": sum(a["status"] == "missing_scan" for a in attempts),
            "duplicate": sum(a["status"] == "duplicate" for a in attempts),
        }
        m = st.columns(3)
        m[0].metric("Charge mismatches", counts["mismatch"])
        m[1].metric("Missing measurements", counts["missing_scan"])
        m[2].metric("Duplicate attempts", counts["duplicate"])

        if pending:
            st.markdown("### Exceptions requiring a decision")
            for attempt in pending:
                title = f"{attempt['parcel_id']} · {status_label(attempt['status'])} · {money_inr(attempt['billed_amount'])}"
                with st.expander(title):
                    st.write(f"**Warehouse:** {attempt['warehouse_id']}  ·  **Invoice line:** {attempt['invoice_line_id']}")
                    st.write(f"**Finding:** {attempt.get('reason', 'No details available.')}")
                    if attempt["status"] == "mismatch":
                        st.write(f"**Expected:** {attempt['expected_category']} · {money_inr(attempt['expected_charge'])}")
                        if st.button("Apply verified correction", key=f"correct_{attempt['event_id']}", disabled=not reviewer.strip()):
                            resolve_exception(run, attempt["event_id"], "correct_charge", reviewer.strip())
                            add_event(run, f"Finance corrected billing event {attempt['event_id']}.")
                            st.rerun()
                    elif attempt["status"] == "duplicate":
                        st.write("The same parcel ID has already been billed in this run. The second attempt should be voided.")
                        if st.button("Void duplicate attempt", key=f"void_{attempt['event_id']}", disabled=not reviewer.strip()):
                            resolve_exception(run, attempt["event_id"], "void_duplicate", reviewer.strip())
                            add_event(run, f"Finance voided duplicate billing event {attempt['event_id']}.")
                            st.rerun()
                    elif attempt["status"] == "missing_scan":
                        st.warning("Do not approve a charge without a measurement. Switch to Operations → Warehouse and run the re-scan, then return to Interception and verify again.")
            st.info("Correct charge mismatches and void duplicates here. Missing measurements must be re-scanned by Operations and verified again.")
        else:
            st.success("All exceptions have been resolved. The invoice is eligible for Finance approval.")

        totals = invoice_totals(run)
        st.markdown("### Invoice release control")
        total_cols = st.columns(3)
        total_cols[0].metric("Billable lines", totals["included_lines"])
        total_cols[1].metric("Invoice total", money_inr(totals["invoice_total"]))
        total_cols[2].metric("Open exceptions", len(unresolved_attempts(run)))

        if run.get("released"):
            st.success(f"Invoice released by {run['released_by']} at {run['released_at']}.")
            final_lines = [a for a in attempts if a["status"] != "voided"]
            export_cols = ["event_id", "invoice_line_id", "parcel_id", "warehouse_id", "billed_category", "billed_amount", "status", "resolution_note"]
            final_records = [{k: a.get(k, "") for k in export_cols} for a in final_lines]
            st.download_button("Download approved invoice CSV", csv_bytes(final_records), f"{run['run_id']}_approved_invoice.csv", "text/csv", type="primary")
        else:
            resolved_reviewers = {a.get("resolved_by", "").strip() for a in attempts if a.get("resolved_by", "").strip()}
            approver_is_separate = bool(approver.strip()) and approver.strip() != run.get("created_by") and approver.strip() not in resolved_reviewers
            can_release = len(unresolved_attempts(run)) == 0 and approver_is_separate
            if len(unresolved_attempts(run)) == 0 and approver.strip() == run.get("created_by"):
                st.error("The invoice creator cannot approve the same run. Enter a different Finance approver name.")
            elif len(unresolved_attempts(run)) == 0 and approver.strip() in resolved_reviewers:
                st.error("The final approver must be different from the person who resolved billing exceptions.")
            if st.button("Approve and release invoice", type="primary", disabled=not can_release, use_container_width=True):
                try:
                    approve_invoice_release(run, approver.strip())
                    add_event(run, f"Invoice released by {approver.strip()}.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        with st.expander("Audit trail"):
            st.dataframe(pd.DataFrame(run["events"]), use_container_width=True, hide_index=True)

# -------------------------------- Footer -----------------------------------
st.markdown("<div style='margin-top:36px;padding-top:14px;border-top:1px solid #E8E6F2;color:#8A879D;font-size:12px'>PARCELPATH BILLING INTERCEPTOR · DEMONSTRATION ONLY · Fictional data and tariff; no live warehouse, invoice or payment system is connected.</div>", unsafe_allow_html=True)
