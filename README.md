# ParcelPath Billing Interceptor — Streamlit Demonstration

A lightweight, interactive simulation of a warehouse-to-invoice billing control for the fictional ParcelPath × Mitti Foods case.

## What the application demonstrates

1. **Warehouse simulation:** creates 100 fictional parcels and 95 initial measurement scans.
2. **Billing simulation:** creates 102 billing attempts, including 8 deliberate category/charge errors, 5 attempts without a scanner measurement and 2 duplicate attempts.
3. **Independent verification:** calculates the expected charge from the warehouse measurement and the demonstration tariff, then compares it with the billing attempt.
4. **Re-scan:** allows Operations to create measurement events for the 5 initially unscanned parcels.
5. **Finance review:** allows Finance to correct mismatches and void duplicate attempts.
6. **Release gate:** blocks release while exceptions remain unresolved and prevents the run creator or exception reviewer from approving their own run.
7. **Exports:** downloads scanner records, billing attempts, verification results and the approved invoice as CSV.

## Important scope and limitations

- All companies, parcel records, prices and injected errors are fictional demonstration data.
- The included tariff is illustrative and uses volume bands only. It is **not** Mitti's signed contract. A real contract may price on actual weight, volumetric weight, zones, service types, minimum charges or other rules.
- The app simulates the warehouse scanner and ParcelPath billing system. It is not connected to real equipment, ERP, invoice or payment systems.
- Data is held in Streamlit session state. It is suitable for a guided demonstration, but is not permanent storage. A refresh, session expiry or app restart may clear the run.
- The Operations/Finance selector is a **demo role switch**, not secure authentication. Anyone with the public demo link can switch roles.
- The billing calculation is deterministic Python logic. AI is not used to calculate prices or approve charges.
- The application demonstrates the **billing-interception** portion of the Razorpay case. It does not ingest Imran's WhatsApp conversations or automate escalation analysis; do not claim that it does.
- Do not upload real customer, parcel, payment or contract data to this public demonstration.

## Requirements

- Python **3.14 or newer**. The project is configured for your Python 3.14.6 installation.
- Streamlit 1.67.0.
- Pandas 2.3.3.

No Django, Docker, Celery, Redis or database server is required.

## Run on Windows (easiest method)

1. Download and extract the ZIP to a normal folder, for example `C:\Projects\parcelpath-billing-interceptor`.
2. Confirm Python is available. Open PowerShell and run:

   ```powershell
   python --version
   ```

   It should display Python 3.14.6 (or another Python 3.14+ release).

3. Double-click `run_windows.bat` in the extracted folder.
4. The launcher creates `.venv`, installs the dependencies from `requirements.txt`, and starts Streamlit.
5. Open `http://localhost:8501` if the browser does not open automatically.

**Important:** The launcher uses `python`, not `py -3.13` or `py -3.14`. It uses the Python installation available through your Windows PATH.

### If you prefer PowerShell commands

Open PowerShell in the extracted project folder and run:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks virtual-environment activation, run this once in the same terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### If Windows cannot find Python

Run:

```powershell
where.exe python
```

If no executable is listed, rerun the Python installer and enable **Add Python to PATH**, then close and reopen PowerShell. Verify with `python --version` before running the launcher.

## Run the automated tests

With the virtual environment activated:

```powershell
python -m unittest discover -s tests -v
```

The included tests check volume bands, seeded simulation counts, unresolved-exception release blocking, re-scan, mismatch correction, duplicate voiding and separation-of-duties rules.

## Push the project to GitHub

1. Create a new repository on GitHub called `parcelpath-billing-interceptor`. For the simplest setup, make it public. Do not initialise it with a README; this folder already contains one.
2. Open PowerShell in the project folder.
3. Run these commands, replacing the URL with your own GitHub repository URL:

   ```powershell
   git init
   git add .
   git commit -m "Initial ParcelPath Billing Interceptor demo"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/parcelpath-billing-interceptor.git
   git push -u origin main
   ```

4. Do not commit `.venv`, secrets, API keys or real customer data. The `.gitignore` excludes the virtual environment and common local files.

## Deploy a public link with Streamlit Community Cloud

1. Go to https://share.streamlit.io/.
2. Sign in with GitHub and authorise Streamlit to access the repository.
3. Select **Create app** and choose **Yup, I have an app**.
4. Select your repository, branch `main`, and main file path `app.py`.
5. Open **Advanced settings** and select Python **3.14** to match your local setup. Streamlit Community Cloud currently defaults to Python 3.12, so make this selection before deploying.
6. Optionally choose a public app subdomain, such as `parcelpath-billing-interceptor`.
7. Click **Deploy**. Community Cloud installs packages from `requirements.txt` and gives you a public URL ending in `streamlit.app`.
8. Open the link and test the full demonstration journey.

The Python version is selected during deployment. Streamlit's documentation notes that changing the Python version after deployment requires deleting and redeploying the app, so choose 3.14 at the outset.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Suggested five-minute demonstration

1. Overview: explain why parcel charges need an independent check.
2. Warehouse: run the 100-parcel simulation and show the 95 initial scans.
3. Billing: generate 102 billing attempts.
4. Interception: verify the initial results: 87 matched, 8 mismatches, 5 missing scans and 2 duplicates.
5. Operations: re-scan the five missing parcels and verify again.
6. Finance: correct the mismatches, void duplicates and resolve all exceptions.
7. Finance approver: release the cleared invoice using a different approver name.
8. Download the approved invoice CSV.

## Replacing the demo tariff

The sample rate card is defined in `billing_engine.py`. Replace it only after receiving the signed contractual rate card and validating the complete pricing formula with Finance. Do not use the sample prices for real invoices.
