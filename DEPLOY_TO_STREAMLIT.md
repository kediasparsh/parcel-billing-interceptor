# Deploy ParcelPath Billing Interceptor to Streamlit Community Cloud

This project is a simple Streamlit app. Deployment is driven by GitHub; no Docker, Django or server setup is required.

## A. Create a GitHub repository

1. Sign in to GitHub.
2. Create a new repository named `parcelpath-billing-interceptor`.
3. Choose Public for the simplest Community Cloud setup. This demonstration contains fictional data only.
4. Do not add a README, licence or `.gitignore` during repository creation; the project already includes these files.

## B. Push the project

Extract the project ZIP. Open PowerShell in the folder that contains `app.py` and `requirements.txt`, then run:

```powershell
git init
git add .
git commit -m "Initial ParcelPath Billing Interceptor demo"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/parcelpath-billing-interceptor.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. If Git asks you to sign in, complete the browser authentication flow.

## C. Deploy

1. Open https://share.streamlit.io/.
2. Sign in with GitHub and authorise access to the repository.
3. Click **Create app** → **Yup, I have an app**.
4. Select repository `parcelpath-billing-interceptor`.
5. Select branch `main`.
6. Set the main file path to `app.py`.
7. Open **Advanced settings** and choose Python **3.14**.
8. Optionally choose an app URL such as `parcelpath-billing-interceptor` if available.
9. Click **Deploy**.

Community Cloud installs the packages listed in `requirements.txt` and assigns a URL ending in `streamlit.app`.

## D. Test the public URL

Use the app's full journey:

1. Start the 100-parcel simulation.
2. Generate billing attempts.
3. Verify charges and inspect intercepted exceptions.
4. Re-scan missing parcels.
5. Switch to the Finance demo view.
6. Correct mismatches and void duplicates.
7. Release with a different approver name.
8. Download the approved invoice.

## E. Publish changes

After editing the code locally, test it and then run:

```powershell
git add .
git commit -m "Update billing interceptor demo"
git push
```

Community Cloud watches the connected GitHub branch and redeploys when you push changes.

## Important

- Choose Python 3.14 during initial deployment. Community Cloud defaults to Python 3.12; the Python version is set in Advanced settings. Changing it after deployment requires deleting and redeploying the app.
- The public Operations/Finance role selector is not secure authentication. Anyone with the link can switch roles.
- This app uses session-based demonstration data. It is not a persistent invoice or finance system.
- Only fictional sample data should be used. Do not upload real customer or financial data.
- Actual production use would require secure authentication, persistent storage, authoritative scanner and billing integrations, the signed contractual tariff and an approval gate in the real invoice-release system.

Official deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
