"""tracker/db/database.py — Connexion SQLite et initialisation du schéma.

Responsabilité : créer la base de données, les tables et les indexes.
Toutes les requêtes SQL métier sont dans models.py.
"""
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "tracker.db"))

SCHEMA_VERSION = 1

_CREATE_DECKS = """
CREATE TABLE IF NOT EXISTS decks (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    created TEXT NOT NULL
);
"""

_CREATE_MATCHES = """
CREATE TABLE IF NOT EXISTS matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id      INTEGER REFERENCES decks(id),
    result       TEXT,
    opponent     TEXT,
    first_player TEXT,
    season       TEXT,
    captured_at  TEXT NOT NULL,
    raw_ocr_data TEXT
);
"""

_CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_matches_deck    ON matches(deck_id);",
    "CREATE INDEX IF NOT EXISTS idx_matches_season  ON matches(season);",
    "CREATE INDEX IF NOT EXISTS idx_matches_date    ON matches(captured_at);",
]


class DatabaseManager:
    """Gère la connexion SQLite et l'initialisation du schéma."""

    def __init__(self, db_path: str = None):
        self.db_path = os.path.abspath(db_path or DB_PATH)
        self._ensure_data_dir()
        self._initialize()

    def _ensure_data_dir(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _initialize(self) -> None:
        conn = self.connect()
        try:
            conn.execute(_CREATE_DECKS)
            conn.execute(_CREATE_MATCHES)
            conn.execute(_CREATE_SCHEMA_VERSION)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)

            row = conn.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            conn.commit()

            version = conn.execute(
                "SELECT version FROM schema_version"
            ).fetchone()["version"]
            logger.info(
                "Base de données initialisée: %s (schema_version=%d)",
                self.db_path,
                version,
            )
        finally:
            conn.close()

    def connect(self) -> sqlite3.Connection:
        """Retourne une connexion SQLite avec row_factory et WAL activé."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
