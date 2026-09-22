"""Load one read-only server database; visitors never upload files."""
from dataclasses import dataclass
import gzip
import io
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

import requests
import streamlit as st

from app import FIELDS, ROOT, connect
from session_database import SessionDatabase


class DataSourceError(ValueError):
    pass


def setting(name, default=''):
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except FileNotFoundError:
        pass
    return os.getenv(name, default)


@dataclass(frozen=True)
class LocalDatabase:
    path: Path
    years: list


def load_database():
    repo = setting('GITHUB_DATA_REPO').strip().removeprefix('https://github.com/').rstrip('/')
    if not repo:
        path = Path(setting('DATABASE_PATH', 'database/pcards.db'))
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise DataSourceError('The audit database is not connected yet. Please contact the website owner.')
        db = None
        try:
            db = connect(path)
            db.execute('SELECT ' + ','.join(FIELDS) + ' FROM audit LIMIT 0')
            years = [r[0] for r in db.execute('SELECT DISTINCT CalendarYear FROM audit WHERE CalendarYear BETWEEN 1900 AND 2100 ORDER BY CalendarYear DESC')]
            if not years:
                raise DataSourceError('No OSU transactions with usable dates were found.')
            return LocalDatabase(path, years)
        except sqlite3.Error:
            raise DataSourceError('The audit database could not be opened. Please contact the website owner.') from None
        finally:
            if db is not None:
                db.close()

    token = setting('GITHUB_DATA_TOKEN').strip()
    filename = setting('GITHUB_DATA_FILE', 'pcards.db.gz').strip().lstrip('/')
    branch = setting('GITHUB_DATA_BRANCH', 'main').strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not token:
        raise DataSourceError('The private database connection needs to be configured by the website owner.')
    if not filename.endswith('.db.gz') or '..' in filename.split('/'):
        raise DataSourceError('The private database file setting is invalid.')
    url = f'https://api.github.com/repos/{repo}/contents/{quote(filename, safe="/")}'
    try:
        with requests.get(url, params={'ref': branch}, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github.raw+json',
            'X-GitHub-Api-Version': '2022-11-28'}, timeout=(15, 60), stream=True) as response:
            if response.status_code != 200:
                messages = {
                    401: 'Database connection: GitHub rejected the access token. The website owner must check or renew GITHUB_DATA_TOKEN in Streamlit Secrets.',
                    403: 'Database connection: GitHub denied access or limited requests. Check that the token has Contents read access to the data repository and is not awaiting approval.',
                    404: 'Database connection: the file could not be found or accessed. Check that pcards.db.gz is uploaded to the private data repository, the branch and file settings match, and the token can read that repository.',
                    429: 'Database connection: GitHub is temporarily limiting requests. Please try again later.',
                }
                raise DataSourceError(messages.get(response.status_code, 'The database service is temporarily unavailable. Please try again later.'))
            compressed = io.BytesIO()
            for chunk in response.iter_content(1024 * 1024):
                if compressed.tell() + len(chunk) > 30 * 1024 * 1024:
                    raise DataSourceError('The compressed database is too large.')
                compressed.write(chunk)
        compressed.seek(0)
        with gzip.GzipFile(fileobj=compressed) as source:
            data = source.read(150 * 1024 * 1024 + 1)
        return SessionDatabase(data)
    except DataSourceError:
        raise
    except (requests.RequestException, OSError, EOFError, ValueError, sqlite3.Error):
        raise DataSourceError('The audit database could not be loaded. Please contact the website owner.') from None


@st.cache_resource(show_spinner=False)
def get_database():
    # Share only the immutable source file. Each query opens its own read-only
    # connection; filters and results remain in the individual browser session.
    return load_database()
