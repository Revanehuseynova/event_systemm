"""SQLite bağlantısı və sxemin yaradılması."""
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"
DEFAULT_CATEGORIES = ["Konfrans", "Seminar", "Təlim", "Müsabiqə", "Digər"]


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        # isolation_level=None: transaksiyalar BEGIN/COMMIT ilə əl ilə idarə olunur
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            for name in DEFAULT_CATEGORIES:
                conn.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))
        finally:
            conn.close()
