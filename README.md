# ParcelPath Billing Interceptor

**A warehouse-to-invoice billing control simulation for the fictional ParcelPath × Mitti Foods case study.**

[**Open the live demo**](https://parcel-billing-interceptor-aiereioyxofc4qh9mvcmo2.streamlit.app/)

The application demonstrates how a logistics provider can independently verify parcel charges against warehouse measurements, identify unsupported or duplicate billing attempts, route exceptions for Finance review, and prevent an invoice from being marked as released until all exceptions have been resolved.

> **Demonstration only:** ParcelPath, Mitti Foods, all parcel records, the warehouse events, the injected errors and the pricing tariff in this application are fictional. The application is not connected to a live warehouse scanner, ERP, invoicing, payment or finance system.

---

## 1. Business problem

In the case study, ParcelPath overcharged Mitti Foods by approximately **₹11 lakh over three months** because of an error involving parcel-size billing. Mitti's Finance team identified the issue after invoices had already been raised, and its earlier emails had not received a response.

The application explores one preventive control for this problem:

**Verify each proposed parcel charge against the parcel's recorded warehouse measurements before the charge is allowed into the final invoice.**

The demonstration focuses on four situations:

- The billing system assigns the wrong parcel category or charge.
- A charge is generated even though a warehouse measurement is missing.
- The same parcel is billed more than once.
- Finance needs to review and resolve exceptions before invoice release.

The case brief does not provide Mitti's signed tariff or the detailed mechanics of the original ₹11 lakh error. The pricing rules below are therefore illustrative test parameters, not a reconstruction of the actual contract or a confirmed explanation of the historical overcharge.

## 2. Live application

**Demo URL:** https://parcel-billing-interceptor-aiereioyxofc4qh9mvcmo2.streamlit.app/

The public app is intended for a guided demonstration. It uses fictional data and a simulated role selector; it must not be used to process real customer invoices or financial information.

## 3. Application workflow

The application has five navigation areas.

| Area | What it does |
|---|---|
| **Overview** | Explains the control, shows the current run summary and starts a new demonstration. |
| **01 · Warehouse** | Simulates parcel records and scanner measurements. It displays the scan log and allows Operations to re-scan parcels that initially have no measurement record. |
| **02 · Billing** | Simulates ParcelPath's billing system and creates a charge attempt for each parcel, including controlled test errors. |
| **03 · Interception** | Independently calculates the expected category and charge from the warehouse scan and demo tariff, then classifies each billing attempt. |
| **04 · Finance** | Allows the Finance demo role to correct charge mismatches, void duplicate attempts, review totals and release a fully cleared invoice. |

### End-to-end demonstration sequence

1. Select **Operations** in the `DEMO VIEW` selector.
2. Open **Overview** and click **Start 100-parcel simulation**.
3. Open **01 · Warehouse** to inspect the parcel and scanner records. Five parcels initially have no scanner measurement. Select **Re-scan missing parcels** to simulate capturing those measurements.
4. Open **02 · Billing** and click **Generate ParcelPath charges**.
5. Open **03 · Interception** and click **Verify all billing attempts**. Review matched charges, mismatches, missing scans and duplicates.
6. Open **04 · Finance**, switch the demo view to **Finance**, and review the exceptions. Correct charge mismatches and void duplicate attempts. Missing measurements must be re-scanned by Operations, then the charges must be verified again.
7. Enter a final approver name that is different from the run creator and the exception reviewer. Click **Approve and release invoice** after all exceptions are resolved.
8. Download the approved invoice CSV. The app also provides CSV exports for scanner records, billing attempts and verification results.

The application is designed so that an unresolved exception blocks invoice release. The run creator cannot approve their own run, and the final approver must be different from the person who resolved the exceptions.

## 4. Demonstration parameters

The default simulation creates the following controlled scenario.

| Parameter | Default value | Description |
|---|---:|---|
| Parcels in a run | 100 | Fictional parcel master records. |
| Initial scanner measurements | 95 | Five parcels intentionally begin without a scan record. |
| Initial billing attempts | 100 | One primary billing attempt for each parcel. |
| Additional duplicate attempts | 2 | Two extra attempts are generated against parcels that have already been billed. |
| Total billing attempts | 102 | 100 primary attempts plus two duplicates. |
| Deliberate category/charge errors | 8 | Eight scanned parcels are intentionally billed using an incorrect category/charge. |
| Charges without initial scan records | 5 | The billing simulator creates a fallback Medium charge, which the interceptor holds because measurement evidence is missing. |
| Duplicate attempts | 2 | Repeated billing attempts for the same parcel ID. |

### Expected verification results

**Initial verification, before the missing parcels are re-scanned:**

| Result | Expected count |
|---|---:|
| Matched | 87 |
| Charge mismatches | 8 |
| Missing scanner measurement | 5 |
| Duplicate attempts | 2 |
| **Total attempts** | **102** |

**After Operations re-scans the five missing parcels and verification is run again:**

| Result | Expected count |
|---|---:|
| Matched | 89 |
| Charge mismatches | 11 |
| Missing scanner measurement | 0 |
| Duplicate attempts | 2 |
| **Total attempts** | **102** |

The five re-scanned parcels no longer have missing-measurement holds. In this fixed demonstration dataset, three of their original fallback charges do not match the now-available measurements and become charge mismatches; two match the measured category and charge.

After Finance corrects all 11 mismatches and voids the two duplicate attempts, the released invoice contains **100 billable lines**. Voided duplicate attempts are excluded from the invoice total and approved invoice export.

The simulation uses a fixed random seed for repeatable parcel/category/warehouse test data. Event IDs and timestamps are generated for each run and will differ.

## 5. Demo pricing rules

The current application uses a simple **volume-only** tariff for demonstration purposes.

Parcel volume is calculated as:

```text
Volume (cm³) = Length (cm) × Width (cm) × Height (cm)
```

| Demo category | Volume band | Demo charge |
|---|---:|---:|
| Small | 0 to below 5,000 cm³ | ₹45.00 |
| Medium | 5,000 to below 15,000 cm³ | ₹60.00 |
| Large | 15,000 cm³ and above | ₹75.00 |

Boundary values are inclusive at the lower limit and exclusive at the upper limit. For example, exactly 5,000 cm³ is Medium, and exactly 15,000 cm³ is Large.

The simulated scanner also records parcel weight, but **weight is not used in the current demo pricing calculation**. A real logistics contract may use actual weight, volumetric weight, chargeable weight, destination zone, service type, minimum charges, fuel surcharges, taxes or other terms. Those rules must be confirmed from the signed contract and implemented and tested before any real use.

The demo rate-card identifier is `DEMO-2026-01` and the currency is INR.

## 6. Exception handling and approval rules

| Detected condition | Interceptor action | Finance / Operations action |
|---|---|---|
| Category and charge match the measurement and demo tariff | Mark as **Matched** | No correction required. |
| Category or amount differs from the expected value | Mark as **Charge mismatch** and hold | Finance applies the independently calculated correction. |
| No warehouse measurement exists | Mark as **Missing scan** and hold | Operations re-scans the parcel; Finance then reviews the result after re-verification. |
| More than one billing attempt exists for a parcel ID | Mark the subsequent attempt as **Duplicate** and hold | Finance voids the duplicate attempt; the original attempt remains the charge of record. |

Invoice release is blocked until every billing attempt has a cleared status (`matched`, `corrected` or `voided`). The final approver must be different from both the run creator and any person who resolved an exception in that run.

These are application-level demonstration controls. Since the role selector is not secure authentication, the names entered in the demo are labels and do not prove a user's real identity.

## 7. Outputs and downloads

The application can generate the following CSV files:

- **Scanner records:** Parcel ID, warehouse, scanner, dimensions, weight and scan timestamp.
- **Billing attempts:** Billing event ID, invoice line ID, parcel ID, warehouse, attempt number, billed category, billed amount and source.
- **Verification report:** Billed and expected category/amount, result status and reason for the exception.
- **Approved invoice:** Cleared invoice lines, excluding voided duplicate attempts, with the recorded resolution status and note.

## 8. Technology and project structure

The application is intentionally lightweight.

| Technology | Purpose |
|---|---|
| Python | Simulation and billing-verification logic. |
| Streamlit | Web interface and interactive workflow. |
| Pandas | Tabular data preparation and display. |
| Python `decimal` | Currency calculations with decimal precision rather than binary floating-point arithmetic. |
| Python `unittest` | Automated checks for the billing rules and approval controls. |

Pinned dependencies in `requirements.txt`:

```text
streamlit==1.67.0
pandas==2.3.3
```

Project files:

```text
parcelpath-billing-interceptor/
├── app.py                       # Streamlit interface and page flow
├── billing_engine.py            # Demo tariff, charge generation, verification and release rules
├── warehouse_simulator.py       # Parcel and scanner-event simulation
├── finance.py                   # Finance exception resolution and release helpers
├── requirements.txt             # Pinned Python dependencies
├── run_windows.bat              # Windows setup and local launch script
├── .streamlit/config.toml       # Streamlit theme and server settings
└── tests/
    └── test_billing_engine.py   # Automated business-rule tests
```

## 9. Run locally

### Requirements

- Windows, macOS or Linux.
- Python 3.14 or newer.
- Internet access for the initial dependency installation.

### Windows quick start

1. Clone or download this repository.
2. Open the project folder.
3. Confirm Python is available:

   ```powershell
   python --version
   ```

4. Double-click `run_windows.bat`. The script creates a virtual environment, installs `requirements.txt` and launches Streamlit.
5. If the browser does not open automatically, visit `http://localhost:8501`.

### Manual setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Then run the same `pip install` and `streamlit run app.py` commands.

## 10. Run the tests

From the project root, with the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

The included tests cover:

- Volume calculation and category boundaries.
- The expected seeded simulation counts.
- Blocking invoice release while exceptions remain unresolved.
- Re-scanning parcels with missing measurements.
- Correcting charge mismatches and voiding duplicate attempts.
- Preventing the run creator or exception reviewer from acting as the final approver.

## 11. Deployment

The application is deployed on Streamlit Community Cloud and connected to a GitHub repository.

To deploy a copy:

1. Push the project files to a GitHub repository. Keep `app.py` and `requirements.txt` in the repository root.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
3. Create an app and select the repository, branch and `app.py` as the main file.
4. In Advanced settings, select Python 3.14 to match the local setup.
5. Deploy. Streamlit installs the pinned packages from `requirements.txt` and provides a `streamlit.app` URL.

Official guide: [Deploy a Streamlit app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## 12. Scope, assumptions and limitations

This project is an **interactive business-process simulation**, not a production billing integration.

- **Fictional environment:** All companies, records, prices, warehouses and errors are illustrative.
- **No live integrations:** The warehouse scanner and ParcelPath billing system are simulated in Python. No physical scanner, ERP, invoicing platform, payment system or customer account is connected.
- **No real invoice submission:** The app creates a simulated invoice result and CSV download. It does not send an invoice to Mitti or update an external finance system.
- **Session-based state:** Simulation records are held in Streamlit session state. They are not a permanent database and may be lost when the session ends, the app restarts or the session is reset.
- **Demo roles, not authentication:** The Operations/Finance selector only changes the demonstration view. It is not a secure login or access-control system.
- **Illustrative tariff:** The volume-only rate card is not Mitti's contractual pricing schedule. It must not be used to calculate actual customer charges.
- **No AI model is connected in this version:** All charge calculations, exception detection and invoice-release checks use deterministic Python rules. The current application does not call Gemini, ChatGPT or another AI service.
- **No claim about the historical root cause:** The case identifies a parcel-size billing error but does not provide the underlying transaction records or signed tariff. The seeded errors in this simulation are test scenarios, not proof of how the historical ₹11 lakh overcharge occurred.
- **Not for real financial data:** Do not upload or enter real customer, parcel, invoice, payment or contract information into the public demo.

### What would be required for production deployment?

A real implementation would require, at minimum:

1. The signed customer tariff and an approved, version-controlled pricing ruleset.
2. Authenticated integrations with the warehouse measurement source and authoritative billing system.
3. A persistent database and secure document/event storage.
4. Actual user authentication, role-based access and enforced separation of duties.
5. A release control in the authoritative invoicing process—not merely a button in a separate demo app.
6. Audit retention, monitoring, alerting, backup/recovery, security testing and operational support.
7. Parallel-run testing against historical invoices and Finance sign-off before the control is allowed to affect live billing.

---

## Case-study context

This application was developed as a demonstration component for **Case 2: “The Festive Rush – ParcelPath and Mitti Foods”** in the Razorpay GTM Campus Build-a-thon. It focuses on the parcel-size billing overcharge and the preventive invoice-verification control proposed in response to that issue.

The broader case recommendation also addresses service reliability, order-feed delays, customer escalations, limited expansion capacity and Mitti's longer-term growth. Those topics are discussed separately in the case presentation; they are not automated by this application.
