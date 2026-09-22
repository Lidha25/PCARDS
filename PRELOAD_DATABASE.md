# One-time private database setup

Visitors will not need a password or database upload. The server retrieves the database using a private connection that only the website owner configures.

## 1. Create a separate private data repository

On GitHub, create a new repository named **PCARDS-DATA** under **Lidha25**. Select **Private**, and add a README so it has a default branch. Keep your existing **PCARDS** code repository public.

Upload the prepared **`private-data-upload/pcards.db.gz`** file to the root of **PCARDS-DATA**, then Commit changes. Do not extract the `.gz` file and do not put it in the public PCARDS repository. It is a compressed copy of the full database, not source code.

The prepared file is sized for GitHub's 25 MiB browser upload limit. Source: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository

## 2. Give the hosted app read-only access

In GitHub account settings, open **Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.

- Name: `PCARDS Streamlit data reader`
- Resource owner: `Lidha25`
- Expiration: choose a date after the assignment will be graded; renew before it expires if needed.
- Repository access: **Only select repositories → PCARDS-DATA**.
- Repository permissions: **Contents → Read-only**. Metadata read access is normally added automatically. No write permission is needed.

Generate and copy the token. Treat it like a password: paste it only into Streamlit's private Secrets settings, never into GitHub files or chat. GitHub may ask you to confirm your identity.

## 3. Add the connection in Streamlit Secrets

Open your app's settings in Streamlit Community Cloud and find **Secrets**. Keep the existing Gemini settings and add the data settings:

```toml
GEMINI_API_KEY = "your-existing-Gemini-key"
GEMINI_MODEL = "gemini-3.6-flash"
GITHUB_DATA_REPO = "Lidha25/PCARDS-DATA"
GITHUB_DATA_FILE = "pcards.db.gz"
GITHUB_DATA_BRANCH = "main"
GITHUB_DATA_TOKEN = "paste-your-read-only-GitHub-token-here"
```

Use the actual default branch name if it is not `main`. Save Secrets. Do not share a screenshot that shows the values.

## 4. Update the website code

Upload the updated source ZIP's contents to **PCARDS** and commit. Streamlit will redeploy. If you change only the database file later, reboot the Streamlit app to reload its cached database.

The app reads the private file using GitHub's repository contents API and a server-side authorization header. The GitHub token and raw database download are never embedded in the page. Reference: https://docs.github.com/en/rest/repos/contents

If the app cannot connect, check that the token is unexpired, the repository is selected for the token, Contents has Read-only access, and the filename/branch match the Secrets settings. The frontend intentionally displays a generic connection error without exposing credentials.
