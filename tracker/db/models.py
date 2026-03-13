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
ALLOWED_MATCH_FIELDS = {"result", "opponent", "opponent_deck", "first_player", "season",
                        "notes", "tags", "energy_type", "conceded_by",
                        "opponent_energy_type", "player_points", "opponent_points",
                        "turns_played", "damage_dealt",
                        "match_type", "rank_name", "rank_points"}


class Models:
    """Requêtes SQL pour decks, matches et stats."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    def _connect(self):
        return self._db.connect()

    # -------------------------------------------------------------------------
    # Decks
    # -------------------------------------------------------------------------

    def create_deck(self, name: str, energy_type: str = None) -> dict:
        created = datetime.now().isoformat()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO decks (name, created, energy_type) VALUES (?, ?, ?)",
                (name, created, energy_type),
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

    def update_deck(self, deck_id: int, name: str, energy_type: str = None) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE decks SET name = ?, energy_type = ? WHERE id = ?",
                (name, energy_type, deck_id),
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
                   (deck_id, result, opponent, opponent_deck, first_player, season, captured_at,
                    raw_ocr_data, notes, tags, turns_played, player_points, opponent_points,
                    damage_dealt, match_type, energy_type, conceded_by, rank_name, rank_points,
                    opponent_energy_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match_data.get("deck_id"),
                    match_data.get("result", "?"),
                    match_data.get("opponent", "?"),
                    match_data.get("opponent_deck"),
                    match_data.get("first_player", "?"),
                    match_data.get("season"),
                    match_data.get("captured_at", datetime.now().isoformat()),
                    match_data.get("raw_ocr_data"),
                    match_data.get("notes"),
                    match_data.get("tags"),
                    match_data.get("turns_played"),
                    match_data.get("player_points"),
                    match_data.get("opponent_points"),
                    match_data.get("damage_dealt"),
                    match_data.get("match_type"),
                    match_data.get("energy_type"),
                    match_data.get("conceded_by"),
                    match_data.get("rank_name"),
                    match_data.get("rank_points"),
                    match_data.get("opponent_energy_type"),
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
        match_type: Optional[str] = None,
        deck_id: Optional[int] = None,
    ) -> list:
        conn = self._connect()
        try:
            sql = "SELECT * FROM matches WHERE 1=1"
            params = []
            if season is not None:
                sql += " AND season = ?"
                params.append(season)
            if match_type is not None:
                sql += " AND match_type = ?"
                params.append(match_type)
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

    def get_stats(self, season: Optional[str] = None,
                  match_type: Optional[str] = None) -> dict:
        conn = self._connect()
        try:
            # Params doublés pour le pattern (? IS NULL OR col = ?)
            _p = (season, season, match_type, match_type)

            # Stats globales (total inclut les "?", winrate les exclut)
            global_row = conn.execute(
                """SELECT
                       COUNT(*) AS total_matches,
                       SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN result = 'L' THEN 1 ELSE 0 END) AS losses
                   FROM matches
                   WHERE (? IS NULL OR season = ?)
                     AND (? IS NULL OR match_type = ?)""",
                _p,
            ).fetchone()

            total = global_row["total_matches"] or 0
            wins = global_row["wins"] or 0
            losses = global_row["losses"] or 0
            known = wins + losses
            winrate = round(wins / known * 100, 1) if known > 0 else 0.0

            # Stats par deck (LEFT JOIN : decks sans match apparaissent quand même)
            deck_rows = conn.execute(
                """SELECT
                       d.id          AS deck_id,
                       d.name        AS deck_name,
                       d.energy_type AS energy_type,
                       COUNT(m.id) AS total,
                       SUM(CASE WHEN m.result = 'W' THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN m.result = 'L' THEN 1 ELSE 0 END) AS losses
                   FROM decks d
                   LEFT JOIN matches m
                       ON m.deck_id = d.id
                       AND (? IS NULL OR m.season = ?)
                       AND (? IS NULL OR m.match_type = ?)
                   GROUP BY d.id, d.name""",
                _p,
            ).fetchall()

            deck_stats = []
            for row in deck_rows:
                d_wins = row["wins"] or 0
                d_losses = row["losses"] or 0
                d_known = d_wins + d_losses
                deck_stats.append({
                    "deck_id": row["deck_id"],
                    "deck_name": row["deck_name"],
                    "energy_type": row["energy_type"] or None,
                    "total": row["total"] or 0,
                    "wins": d_wins,
                    "losses": d_losses,
                    "winrate": round(d_wins / d_known * 100, 1) if d_known > 0 else 0.0,
                })

            deck_stats.sort(key=lambda x: x["wins"], reverse=True)

            # Série en cours (max 50 derniers matchs W/L)
            recent_rows = conn.execute(
                """SELECT result FROM matches
                   WHERE (? IS NULL OR season = ?) AND (? IS NULL OR match_type = ?)
                     AND result IN ('W', 'L')
                   ORDER BY captured_at DESC LIMIT 50""",
                _p,
            ).fetchall()
            current_streak_type = None
            current_streak_count = 0
            if recent_rows:
                current_streak_type = recent_rows[0]["result"]
                for row in recent_rows:
                    if row["result"] == current_streak_type:
                        current_streak_count += 1
                    else:
                        break

            # Meilleure série de victoires
            all_rows = conn.execute(
                """SELECT result FROM matches
                   WHERE (? IS NULL OR season = ?) AND (? IS NULL OR match_type = ?)
                     AND result IN ('W', 'L')
                   ORDER BY captured_at ASC""",
                _p,
            ).fetchall()
            best_streak = 0
            run = 0
            for row in all_rows:
                if row["result"] == "W":
                    run += 1
                    if run > best_streak:
                        best_streak = run
                else:
                    run = 0

            # Deck le plus joué
            top_row = conn.execute(
                """SELECT d.name, COUNT(*) AS total
                   FROM matches m JOIN decks d ON m.deck_id = d.id
                   WHERE (? IS NULL OR m.season = ?) AND (? IS NULL OR m.match_type = ?)
                   GROUP BY m.deck_id ORDER BY total DESC LIMIT 1""",
                _p,
            ).fetchone()
            top_deck = {"name": top_row["name"], "total": top_row["total"]} if top_row else None

            return {
                "total_matches": total,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "deck_stats": deck_stats,
                "current_streak": {"type": current_streak_type, "count": current_streak_count},
                "best_win_streak": best_streak,
                "top_deck": top_deck,
            }
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Deck detection mappings
    # -------------------------------------------------------------------------

    def upsert_deck_detection(self, detected_name: str, energy_type: str) -> dict:
        """Insère ou incrémente une détection de deck. Retourne la ligne."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM deck_detection_mappings WHERE detected_name = ? AND (energy_type = ? OR energy_type IS NULL)",
                (detected_name, energy_type),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE deck_detection_mappings SET seen_count = seen_count + 1, energy_type = ? WHERE id = ?",
                    (energy_type, row["id"]),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM deck_detection_mappings WHERE id = ?", (row["id"],)
                ).fetchone()
            else:
                cursor = conn.execute(
                    "INSERT INTO deck_detection_mappings (detected_name, energy_type) VALUES (?, ?)",
                    (detected_name, energy_type),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM deck_detection_mappings WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_deck_mappings(self) -> list:
        """Retourne tous les mappings (confirmés et en attente), triés par vus en dernier."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT m.*, d.name AS deck_name
                   FROM deck_detection_mappings m
                   LEFT JOIN decks d ON m.deck_id = d.id
                   ORDER BY m.confirmed DESC, m.seen_count DESC"""
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def save_deck_mapping(self, mapping_id: int, deck_id: int) -> bool:
        """Confirme un mapping : associe un deck_id à une détection."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE deck_detection_mappings SET deck_id = ?, confirmed = 1 WHERE id = ?",
                (deck_id, mapping_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_deck_mapping(self, mapping_id: int) -> bool:
        """Supprime un mapping."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM deck_detection_mappings WHERE id = ?", (mapping_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def find_deck_by_detection(self, detected_name: str, energy_type: str) -> Optional[int]:
        """Cherche un deck_id confirmé pour une détection donnée."""
        conn = self._connect()
        try:
            row = conn.execute(
                """SELECT deck_id FROM deck_detection_mappings
                   WHERE confirmed = 1 AND deck_id IS NOT NULL
                   AND detected_name = ? AND (energy_type = ? OR energy_type IS NULL)
                   LIMIT 1""",
                (detected_name, energy_type),
            ).fetchone()
            return row["deck_id"] if row else None
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Opponent deck archetypes
    # -------------------------------------------------------------------------

    def get_opponent_archetypes(self) -> list:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, name, key_pokemon, notes FROM opponent_deck_archetypes ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def save_opponent_archetype(self, archetype_id, name: str, key_pokemon: str, notes: str = None):
        conn = self._connect()
        try:
            if archetype_id:
                conn.execute(
                    "UPDATE opponent_deck_archetypes SET name=?, key_pokemon=?, notes=? WHERE id=?",
                    (name, key_pokemon, notes, archetype_id)
                )
                result = {"id": archetype_id, "name": name, "key_pokemon": key_pokemon, "notes": notes}
            else:
                cursor = conn.execute(
                    "INSERT INTO opponent_deck_archetypes (name, key_pokemon, notes) VALUES (?,?,?)",
                    (name, key_pokemon, notes)
                )
                result = {"id": cursor.lastrowid, "name": name, "key_pokemon": key_pokemon, "notes": notes}
            conn.commit()
            return result
        finally:
            conn.close()

    def delete_opponent_archetype(self, archetype_id: int) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM opponent_deck_archetypes WHERE id=?", (archetype_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def match_opponent_archetypes(self, pokemon_seen: list) -> list:
        """Score chaque archetype contre les Pokemon détectés. Retourne une liste triée.

        Matching par mots (word-set) : tous les mots du nom-clé doivent apparaître
        comme mots entiers dans le nom détecté.
        Ex : "Dracaufeu ex" → {"dracaufeu","ex"} ne matche PAS "mega-dracaufeu"
             car "ex" est absent. Insensible à la casse et aux accents.
        """
        import unicodedata
        import re

        def norm(s):
            s = unicodedata.normalize("NFD", s.lower().strip())
            return "".join(c for c in s if unicodedata.category(c) != "Mn")

        def words(s):
            return set(w for w in re.split(r"[\s\-_]+", norm(s)) if w)

        archetypes = self.get_opponent_archetypes()
        seen_words = [words(p) for p in pokemon_seen]
        results = []
        for a in archetypes:
            keys = [k.strip() for k in a["key_pokemon"].split("|") if k.strip()]
            matches = []
            for k in keys:
                kw = words(k)
                if kw and any(kw.issubset(sw) for sw in seen_words):
                    matches.append(k)
            if matches:
                results.append({
                    "id": a["id"],
                    "name": a["name"],
                    "score": len(matches),
                    "total": len(keys),
                    "matched": matches,
                })
        results.sort(key=lambda x: (-x["score"], -x["total"]))
        return results

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
