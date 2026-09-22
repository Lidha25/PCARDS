# Streamlit Community Cloud deployment

Public code repository: https://github.com/Lidha25/PCARDS

This version opens directly with two audit tabs and a calendar-year selector at the top-right. There is no sidebar, visitor upload, or website password.

## Updating the existing live app

1. Complete the private database setup in **[PRELOAD_DATABASE.md](PRELOAD_DATABASE.md)** first.
2. Extract the updated `website-source.zip` and upload its contents to the public PCARDS repository. Replace previous files and Commit changes. Include `hosted_database.py`, `session_database.py`, `streamlit_app.py`, updated dependencies and `.streamlit/config.toml`.
3. Streamlit redeploys when the GitHub files change. The main file remains `streamlit_app.py`.
4. Verify both tabs appear without asking for a file. Select 2014 at the top-right, search Description for `alcohol`, try Vendor search, and ask a Gemini question.

Never upload `.env`, `.streamlit/secrets.toml`, either database file, or the `private-data-upload` folder to the public code repository. The source ZIP excludes them. `.env.example` contains only placeholders.

## New deployment

1. Sign in at https://share.streamlit.io/ with GitHub and choose Create app.
2. Select `Lidha25/PCARDS`, the branch containing your files (usually `main`), and main file `streamlit_app.py`.
3. In Advanced settings, use Python 3.12 and enter the private Secrets from PRELOAD_DATABASE.md.
4. Save and deploy. The app receives a public `https://...streamlit.app` link.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Local use

Keep `database/pcards.db` in your project and your Gemini key in the private `.env` file. Run:

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 -m streamlit run streamlit_app.py
```

The database loads automatically. You do not need the GitHub token locally unless you set GITHUB_DATA_REPO to use the remote data source.

## Access and data handling

No website login is required. Anyone who reaches the app can search and export transaction results. The database file's private storage does not make those results private. Gemini receives only typed questions and fixed field definitions; transaction rows are not sent to Gemini. The owner's Gemini quota is used for questions. Per-session rate limiting is a convenience, not a strong account-level spending cap.

The database is downloaded once per server process into a temporary file and shared read-only across visitor sessions. Search results and filters are session-specific. Updating the stored database or its connection settings requires a Streamlit app reboot to clear the cached source. Temporary files are not placed in publicly served folders.

Submit the live app link and the public PCARDS repository link. Parts II and III remain separate assignment work.
