"""One uploaded SQLite file per Streamlit session; never a shared data cache."""
from pathlib import Path
import sqlite3
import tempfile
import weakref

from app import FIELDS, connect


class SessionDatabase:
    def __init__(self, buffer):
        if len(buffer) > 150 * 1024 * 1024:
            raise ValueError('The database must be smaller than 150 MB.')
        if bytes(buffer[:16]) != b'SQLite format 3\x00':
            raise ValueError('Please upload a SQLite database (.db), not a ZIP or spreadsheet.')
        with tempfile.NamedTemporaryFile(prefix='pcard-session-', suffix='.db', delete=False) as file:
            self.path = Path(file.name)
            self._cleanup = weakref.finalize(self, self.path.unlink, missing_ok=True)
            file.write(buffer)
        try:
            with sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True) as db:
                schema = db.execute("SELECT type FROM sqlite_master WHERE name='pcards'").fetchone()
                if not schema or schema[0] != 'table':
                    raise ValueError('The database must contain the pcards transaction table.')
                columns = {row[1] for row in db.execute('PRAGMA table_info(pcards)')}
                if not set(FIELDS).issubset(columns):
                    raise ValueError('The pcards table is missing required transaction fields.')
            db.close()
            db = connect(self.path)
            try:
                self.years = [r[0] for r in db.execute('SELECT DISTINCT CalendarYear FROM audit WHERE CalendarYear BETWEEN 1900 AND 2100 ORDER BY CalendarYear DESC')]
            finally:
                db.close()
            if not self.years:
                raise ValueError('No OSU transactions with usable calendar-year dates were found.')
        except Exception:
            # Close validation connections before deleting the temporary file on Windows.
            if 'db' in locals():
                db.close()
            self.close()
            raise

    def close(self):
        self._cleanup()
