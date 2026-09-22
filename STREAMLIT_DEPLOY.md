# Deploy PCARDS on Streamlit Community Cloud

Your public repository: https://github.com/Lidha25/PCARDS

## 1. Update GitHub

Extract the updated `website-source.zip`. In the repository's Code tab, choose Add file → Upload files. Upload the extracted files and folders, replacing the previous versions, then Commit changes.

Make sure these new files are included:

- `streamlit_app.py` — the Streamlit entry point
- `session_database.py` — handles the session's uploaded database
- `.streamlit/config.toml` — theme and upload settings
- Updated `app.py`, `requirements.txt`, and README

Do not upload your actual `.env`, `.streamlit/secrets.toml`, database, or exported results. `.env.example` contains only placeholders and is safe.

## 2. Create the Streamlit app

1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Choose **Create app** and deploy from an existing GitHub repository.
3. Select repository **Lidha25/PCARDS**.
4. Select the branch containing your uploaded files (usually `main`; check GitHub).
5. Set **Main file path** to **`streamlit_app.py`**. Do not use `app.py`, which is the earlier Flask entry point.
6. In **Advanced settings**, choose Python **3.12** if available.
7. In the private **Secrets** box, paste the following, replacing only the placeholder with your actual key:

```toml
GEMINI_API_KEY = "paste-your-real-key-here"
GEMINI_MODEL = "gemini-3.6-flash"
```

Do not paste this completed secret into GitHub, a screenshot, or a chat. Your existing API key remains usable; there is no need to create another key just for Streamlit.

8. Click **Deploy**. Streamlit installs the packages and displays your live `https://…streamlit.app` link. If it reports an error, share the error text without secrets.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## 3. Load the database into your session

The app opens without a password. Its sidebar has **Select pcards.db**. Upload your local `database/pcards.db` there — not on GitHub. Your existing file is approximately 99 MiB and fits the app's 150 MB upload limit.

This is a per-session upload: a new visitor uploads their own database file. A refresh or new session may require another upload. Give the instructor the original database through the course's approved private file-sharing channel if they do not already have it. The live link alone does not include a preloaded database.

The upload is transferred to Streamlit's hosting server for processing. The application stores a uniquely named temporary file for that session, never in a global shared data cache. The **Clear uploaded database** button closes the database and deletes that temporary file. Session disposal also schedules cleanup, but immediate deletion on closing the browser is not guaranteed. Upload only data you are permitted to process on that hosting service.

Gemini receives your typed question and a fixed field description. It does not receive database rows or the database file. The Gemini key stays in server-side Secrets. Because the app has no login, visitors use the owner's Gemini quota; the included per-session question limit is not a strong account-level spending cap.

## 4. Test and submit

1. Select calendar year 2014.
2. Search Description for `alcohol`.
3. Search Vendor for `USPS` (zero matches is a valid result).
4. Ask “Show transactions with alcohol in the description.”
5. Prepare and download a CSV of matching records.
6. Click Clear uploaded database and confirm the app asks for a file again.

Submit your live Streamlit link and https://github.com/Lidha25/PCARDS. Parts II and III remain for you to complete later.

## Run the Streamlit version locally

In your website folder:

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 -m streamlit run streamlit_app.py
```

Open the address printed by Streamlit, normally http://localhost:8501. Upload `pcards.db` in the sidebar. Local runs can use your existing private `.env`; Community Cloud uses Secrets instead. No auditor password, SECRET_KEY or COOKIE_SECURE setting is required.
