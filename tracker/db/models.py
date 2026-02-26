"""tracker/db/models.py — Toutes les requêtes SQL.

Règle critique : aucun SQL en dehors de ce fichier.
Thread safety : le threading.Lock est sous la responsabilité de l'appelant (TrackerAPI).
"""
import logging
from datetime import datetime
from typing import Optional

from .database import DatabaseManager

logger = logging.getLogger(__name__)

# Whitelist des champs modifiables via update_match_field.
# Empêche toute injection SQL par nom de champ.
ALLOWED_MATCH_FIELDS = {"result", "opponent", "first_player", "season"}


class Models:
    """Requêtes SQL pour decks, matches et stats."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    def _connect(self):
        return self._db.connect()

    # -------------------------------------------------------------------------
    # Decks
    # -------------------------------------------------------------------------

    def create_deck(self, name: str) -> dict:
        created = datetime.now().isoformat()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO decks (name, created) VALUES (?, ?)", (name, created)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM decks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_decks(self) -> list:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM decks ORDER BY created ASC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_deck(self, deck_id: int, name: str) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE decks SET name = ? WHERE id = ?", (name, deck_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_deck(self, deck_id: int) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Matches
    # -------------------------------------------------------------------------

    def save_match(self, match_data: dict) -> dict:
        conn = self._connect()
        try:
            cursor = conn.execute(
                """INSERT INTO matches
                   (deck_id, result, opponent, first_player, season, captured_at, raw_ocr_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    match_data.get("deck_id"),
                    match_data.get("result", "?"),
                    match_data.get("opponent", "?"),
                    match_data.get("first_player", "?"),
                    match_data.get("season"),
                    match_data.get("captured_at", datetime.now().isoformat()),
                    match_data.get("raw_ocr_data"),
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM matches WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_matches(
        self,
        season: Optional[str] = None,
        deck_id: Optional[int] = None,
    ) -> list:
        conn = self._connect()
        try:
            sql = "SELECT * FROM matches WHERE 1=1"
            params = []
            if season is not None:
                sql += " AND season = ?"
                params.append(season)
            if deck_id is not None:
                sql += " AND deck_id = ?"
                params.append(deck_id)
            sql += " ORDER BY captured_at DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_match(self, match_id: int) -> bool:
        """Supprime un match. Retourne True si supprimé, False si introuvable."""
        conn = self._connect()
        try:
            cursor = conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_seasons(self) -> list:
        """Retourne les saisons distinctes (non nulles) triées DESC."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT season FROM matches WHERE season IS NOT NULL ORDER BY season DESC"
            ).fetchall()
            return [row["season"] for row in rows]
        finally:
            conn.close()

    def update_match_field(self, match_id: int, field: str, value: str) -> bool:
        if field not in ALLOWED_MATCH_FIELDS:
            logger.warning("update_match_field: champ non autorisé '%s'", field)
            return False
        conn = self._connect()
        try:
            # field est validé contre ALLOWED_MATCH_FIELDS — pas d'injection possible
            cursor = conn.execute(
                f"UPDATE matches SET {field} = ? WHERE id = ?", (value, match_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def get_stats(self, season: Optional[str] = None) -> dict:
        conn = self._connect()
        try:
            season_params = (season, season)

            # Stats globales (total inclut les "?", winrate les exclut)
            global_row = conn.execute(
                """SELECT
                       COUNT(*) AS total_matches,
                       SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN result = 'L' THEN 1 ELSE 0 END) AS losses
                   FROM matches
                   WHERE (? IS NULL OR season = ?)""",
                season_params,
            ).fetchone()

            total = global_row["total_matches"] or 0
            wins = global_row["wins"] or 0
            losses = global_row["losses"] or 0
            known = wins + losses
            winrate = round(wins / known * 100, 1) if known > 0 else 0.0

            # Stats par deck (LEFT JOIN : decks sans match apparaissent quand même)
            deck_rows = conn.execute(
                """SELECT
                       d.id   AS deck_id,
                       d.name AS deck_name,
                       COUNT(m.id) AS total,
                       SUM(CASE WHEN m.result = 'W' THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN m.result = 'L' THEN 1 ELSE 0 END) AS losses
                   FROM decks d
                   LEFT JOIN matches m
                       ON m.deck_id = d.id
                       AND (? IS NULL OR m.season = ?)
                   GROUP BY d.id, d.name""",
                season_params,
            ).fetchall()

            deck_stats = []
            for row in deck_rows:
                d_wins = row["wins"] or 0
                d_losses = row["losses"] or 0
                d_known = d_wins + d_losses
                deck_stats.append({
                    "deck_id": row["deck_id"],
                    "deck_name": row["deck_name"],
                    "total": row["total"] or 0,
                    "wins": d_wins,
                    "losses": d_losses,
                    "winrate": round(d_wins / d_known * 100, 1) if d_known > 0 else 0.0,
                })

            deck_stats.sort(key=lambda x: x["wins"], reverse=True)

            return {
                "total_matches": total,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "deck_stats": deck_stats,
            }
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Schema
    # -------------------------------------------------------------------------

    def get_schema_version(self) -> Optional[int]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            return row["version"] if row else None
        finally:
            conn.close()
