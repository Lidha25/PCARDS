# OSU P-card Audit Workspace

## Streamlit Community Cloud (recommended for this assignment)

The Streamlit version is ready in **`streamlit_app.py`**. Follow **[STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md)** to update your public GitHub repository and deploy it. Choose `streamlit_app.py` as the main file, and put the Gemini key in Community Cloud's private Secrets settings.

Run locally with `python -m streamlit run streamlit_app.py`. The app automatically uses your existing `database/pcards.db`. On Community Cloud, it loads `pcards.db.gz` from a separate private GitHub data repository using credentials in Streamlit Secrets. See **[PRELOAD_DATABASE.md](PRELOAD_DATABASE.md)** for the one-time setup. Visitors see both tabs immediately, select the calendar year at the top-right, and can search without a password or file upload. The source database is shared read-only; each visitor's filters and results stay in their own session. Password-free visitors can view and export matching records even though the underlying GitHub file is private.

The older Flask version remains available in `app.py`. The sections below describe that version; deploy `streamlit_app.py` on Streamlit Community Cloud.

Two tabs: an audit dashboard with independent description/vendor searches, and natural-language database questions powered by Gemini. Both local and hosted versions open directly without a password. The application reads the existing `pcards` SQLite table, limits results to OSU (AgencyNumber 1000), and derives calendar years from TransactionDate, not the supplied Year field.

Anyone who can reach the website can search and download transaction results and use the Gemini question feature. The database file and API key remain on the server, but the transaction results are not confidential on a publicly reachable deployment.

## Run on your computer

1. Install Python 3.11 or later.
2. Open a terminal in this folder and run `pip install -r requirements.txt`.
3. Keep the database at `database/pcards.db` (the root-level copy is not used).
4. Keep your existing `.env` file private. Add missing settings from `.env.example`; do not overwrite your existing API key. `GEMINI_API_KEY` is the supported key name.
5. Run `python app.py` (or `py -3.14 app.py` on Windows) and open http://localhost:8000. The dashboard opens directly.

No `AUDITOR_PASSWORD`, `SECRET_KEY`, or `COOKIE_SECURE` setting is needed. If those settings already exist in `.env`, they are ignored. Keep the terminal open while using the website. After updating the files, stop the running server with Ctrl+C, start it again, and refresh the browser.

The dashboard works without Gemini. Natural-language questions need a valid key and an available Gemini model. The default is `gemini-3.6-flash`, verified with this project's key during setup; change `GEMINI_MODEL` in private settings if your account uses a different model. The app uses the operating system's trusted certificates for HTTPS connections.

## GitHub and live hosting

GitHub stores source code. GitHub Pages cannot run this Python backend or privately query SQLite. Use a Python/Docker hosting service with HTTPS and private persistent storage, or an institution-managed server.

1. Create your GitHub repository and upload only source files: app.py, requirements.txt, templates/, static/, Dockerfile, .dockerignore, .gitignore, .env.example, README.md, and tests/.
2. **Never upload `.env`, either copy of `pcards.db`, the database folder, or exports.** `.gitignore` protects normal Git workflows; manual browser uploads must be checked separately. Do not put the database in a public repository or a public download URL. If your course requires a public repository, source code alone can be public.
3. Deploy the repository with the Dockerfile, or install requirements and start `python app.py` on a Python host. Set the host's port setting via `PORT` if needed.
4. Privately transfer `pcards.db` to the host's persistent storage (for example `/data/pcards.db`). Set `DATABASE_PATH` to that location. Mount it read-only for the application when supported. Do not include it in the public image or static folder.
5. In the host's private environment settings, set `GEMINI_API_KEY`, `GEMINI_MODEL`, and `DATABASE_PATH`. Enable HTTPS.
6. Open the live site, select 2014, and test both search fields and an AI question. No login is needed. Direct requests for `/pcards.db`, `/database/pcards.db`, and `/.env` must return 404.
7. Submit the live HTTPS link and GitHub repository link.

This version intentionally has no authentication and sets no session cookies. It retains request validation, browser cross-site request checks, read-only database connections and Gemini rate limits. These do not restrict who may access transaction results. Gemini calls from visitors use the owner's API quota. Run a single application process for the included in-memory rate limits; use a shared rate-limit store or gateway before scaling to multiple processes.

## Dashboard

Select a calendar year. Description search examines only Description; Vendor search examines only Vendor. Each matches a case-insensitive literal substring, including literal `%` and `_`. The 14 policy categories provide suggested keywords. Clicking a suggestion fills the fields but does not execute a search. Search results include transaction ID, dates, amount, vendor, description, cardholder and agency information. Paging shows 50 records. CSV downloads include all matches up to 10,000 rows; narrow larger searches. Text values that could become spreadsheet formulas are escaped on export.

Keyword matches are potential exceptions, not findings of fraud or confirmed violations. Suggestions may produce false positives and miss prohibited purchases. Review receipts, business purpose and approvals. Returns and credits are retained in the net amount.

## Natural-language questions and privacy

Only the typed question and a fixed field/capability description go to Gemini. Database rows, cardholder lists, query results and the database file are never sent. Auditors should not type confidential information into questions. The AI returns a limited query plan; the server validates its field names and operations and uses parameterized SQL. It never executes AI-generated SQL or code. The selected year and OSU scope are enforced by the server.

Examples: "Show transactions with postage in the description", "Show total spending by vendor", "How many transactions have amounts of at least $5,000?" Supported: transaction lists, counts/net totals, group totals, text substring filters combined with AND, inclusive amount bounds. Unsupported questions (for example split purchases, duplicates, OR conditions, averages or date ranges) should produce a request to rephrase. Model interpretation can be imperfect: the UI displays applied filters so the auditor can check them. Summary answers are calculated from SQLite, not invented by Gemini.

Implementation references: [Gemini generateContent](https://ai.google.dev/api/generate-content), [Flask security](https://flask.palletsprojects.com/en/stable/web-security/).

## Checks

Run `python -m unittest discover -s tests -v`. Tests use a small temporary database and mocked Gemini responses; they do not use your key. They check password-free HTTP/HTTPS access without session cookies, direct-file protection, cross-site request checks, OSU/calendar-year scope, independent search fields, literal search text, numeric totals, injection resistance, and exports.

Parts II and III of the assignment are intentionally left for later. No live website or GitHub repository is created by these local files.
