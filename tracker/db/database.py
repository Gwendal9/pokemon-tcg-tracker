"""tracker/db/database.py — Connexion SQLite et initialisation du schéma.

Responsabilité : créer la base de données, les tables et les indexes.
Toutes les requêtes SQL métier sont dans models.py.
"""
import logging
import os
import sqlite3

from tracker.paths import get_data_dir

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(get_data_dir(), "tracker.db")

SCHEMA_VERSION = 14

_ARCHETYPES_DATA = [
    # (name, key_pokemon, notes)
    # key_pokemon = noms FR tels qu'ils apparaissent dans le jeu (version FR)
    # Separateur | entre chaque Pokemon cle du deck
    # Inclure les formes pre-evoluees pour maximiser les chances de detection OCR

    # =========================================================================
    # B1 — Fantastical Parade (Mega Evolutions) — SET ACTUEL S/A-TIER
    # =========================================================================

    # S-TIER
    ("Mega Altaria ex / Amphinobi",
     "Mega Altaria ex|Altaria|Tylton|Amphinobi|Grenousse|Croâporal|Korillon",
     "S-Tier B1 — FR: Tylton(Swablu), Altaria, Mega Altaria ex, Amphinobi(Greninja), Korillon(Chingling)"),

    ("Mega Altaria ex / Banshitrouye",
     "Mega Altaria ex|Altaria|Tylton|Banshitrouye|Pitrouille|Korillon",
     "S-Tier B1 — FR: Mega Altaria ex, Banshitrouye(Gourgeist), Pitrouille(Pumpkaboo), Korillon(Chingling)"),

    ("Mega Absol ex / Trioxhydre",
     "Mega Absol ex|Absol|Trioxhydre|Diamat|Solochi",
     "S-Tier B1 — FR: Mega Absol ex, Absol, Trioxhydre(Hydreigon), Diamat(Zweilous), Solochi(Deino)"),

    ("Mega Absol ex / Amphinobi",
     "Mega Absol ex|Absol|Amphinobi|Grenousse|Croâporal|Korillon",
     "A+Tier B1 — FR: Mega Absol ex, Absol, Amphinobi(Greninja), Korillon(Chingling)"),

    # A-TIER
    ("Mega Altaria ex / Korillon",
     "Mega Altaria ex|Altaria|Tylton|Korillon",
     "A-Tier B1 — variante Korillon(Chingling) pour bloquer les Items adverses"),

    ("Mega Dracaufeu Y ex / Entei ex",
     "Mega Dracaufeu Y ex|Dracaufeu ex|Reptincel|Salamèche|Entei ex",
     "A-Tier B1 — FR: Mega Dracaufeu Y ex, Entei ex"),

    ("Mega Braségali ex / Castorno",
     "Mega Braségali ex|Braségali ex|Braségali|Poussifeu|Castorno",
     "A-Tier B1 — FR: Mega Braségali ex(Blaziken), Castorno(Heatmor)"),

    # =========================================================================
    # B1a — Paldean Wonders — SET ACTUEL
    # =========================================================================

    # A+/A-TIER
    ("Amphinobi ex / Suicune ex",
     "Amphinobi ex|Grenousse|Croâporal|Suicune ex",
     "A+Tier B1a — FR: Amphinobi ex(Greninja ex), Suicune ex"),

    ("Magnézone / Ampibidou ex",
     "Magnézone|Magnéton|Magnéti|Ampibidou ex|Ampibidou|Têtampoule|Plumeline|Zeraora",
     "A+Tier B1a — FR: Magnézone, Magnéti(Magnemite), Ampibidou ex(Bellibolt ex), Plumeline(Oricorio)"),

    ("Magnézone / Plumeline",
     "Magnézone|Magnéton|Magnéti|Plumeline|Zeraora",
     "A-Tier B1a — FR: Magnézone + Plumeline(Oricorio Pompon) Safeguard"),

    ("Baojian ex / Glaivodo",
     "Baojian ex|Glaivodo|Cryodo|Frigodo|Suicune ex",
     "A-Tier B1a — FR: Baojian ex(Chien-Pao ex), Glaivodo(Baxcalibur), Frigodo(Frigibax), Cryodo(Arctibax)"),

    ("Ogerpon Masque Turquoise ex / Phyllali ex",
     "Ogerpon Masque Turquoise ex|Ogerpon|Phyllali ex|Phyllali|Evoli|Évoli",
     "A-Tier B1a — FR: Ogerpon Masque Turquoise ex, Phyllali ex(Leafeon ex), Évoli(Eevee)"),

    ("Gromago ex",
     "Gromago ex|Gromago|Mordudor|Mordudor Coffre",
     "B1a — FR: Gromago ex(Gholdengo ex), Mordudor(Gimmighoul)"),

    # =========================================================================
    # A2 / A2a / A2b — Space-Time Smackdown / Triumphant Light / Shining Rev.
    # =========================================================================

    ("Giratina ex / Mimiqui",
     "Giratina ex|Giratina|Mimiqui",
     "A2 — FR: Giratina ex, Mimiqui(Mimikyu)"),

    ("Darkrai ex / Giratina ex",
     "Darkrai ex|Darkrai|Giratina ex|Giratina|Nosférapti|Nostenfer",
     "A2 — FR: Darkrai ex, Giratina ex, Nosférapti(Zubat), Nostenfer(Crobat)"),

    ("Raikou ex / Tapu Koko ex",
     "Raikou ex|Raikou|Tapu Koko ex|Tapu Koko|Magnézone|Magnéti",
     "A2 — FR: Raikou ex, Tapu Koko ex, Magnézone"),

    ("Dialga ex",
     "Dialga ex|Dialga",
     "A2 Space-Time Smackdown — Acier/Dragon"),

    ("Palkia ex",
     "Palkia ex|Palkia",
     "A2 Space-Time Smackdown — Eau/Dragon"),

    # =========================================================================
    # A1a — Mythical Island
    # =========================================================================

    ("Mew ex / Mewtwo ex",
     "Mew ex|Mew|Mewtwo ex|Mewtwo",
     "A1a Mythical Island — FR: Mew ex, Mewtwo ex"),

    ("Celebi ex / Noeunoeuf",
     "Celebi ex|Celebi|Noeunoeuf|Noadkoko ex|Noadkoko",
     "A1a — FR: Celebi ex, Noeunoeuf(Exeggcute), Noadkoko ex(Exeggutor ex)"),

    # =========================================================================
    # A1 — Genetic Apex (decks encore joues occasionnellement)
    # =========================================================================

    ("Dracaufeu ex",
     "Dracaufeu ex|Reptincel|Salamèche|Sulfura ex",
     "A1 Genetic Apex — FR: Dracaufeu ex(Charizard ex), Reptincel(Charmeleon), Salamèche(Charmander), Sulfura ex(Moltres ex)"),

    ("Pikachu ex",
     "Pikachu ex|Raichu|Electhor ex",
     "A1 Genetic Apex — FR: Pikachu ex, Raichu, Electhor ex(Zapdos ex)"),

    ("Mewtwo ex / Gardevoir",
     "Mewtwo ex|Mewtwo|Gardevoir|Kirlia|Tarsal",
     "A1 Genetic Apex — FR: Mewtwo ex, Gardevoir, Kirlia, Tarsal(Ralts)"),

    ("Léviator ex",
     "Léviator ex|Léviator|Magicarpe",
     "A1 Genetic Apex — FR: Léviator ex(Gyarados ex), Magicarpe(Magikarp)"),

    ("Arcanin ex",
     "Arcanin ex|Caninos|Sulfura ex",
     "A1 Genetic Apex — FR: Arcanin ex(Arcanine ex), Caninos(Growlithe), Sulfura ex(Moltres ex)"),

    ("Artikodin ex",
     "Artikodin ex|Artikodin",
     "A1 Genetic Apex — FR: Artikodin ex(Articuno ex)"),

    ("Staross ex",
     "Staross ex|Staross|Stari",
     "A1 Genetic Apex — FR: Staross ex(Starmie ex), Stari(Staryu)"),

    ("Smogogo / Miascuts Couronne ex",
     "Smogogo|Smogo|Miascuts Couronne ex|Miascuts",
     "A1 — FR: Smogogo(Weezing), Smogo(Koffing) + Miascuts Couronne ex(Pecharunt ex)"),
]


def _seed_archetypes(conn) -> None:
    """Insere les archetypes meta manquants (par nom) sans ecraser les entrees existantes."""
    existing_names = {
        row[0].lower()
        for row in conn.execute("SELECT name FROM opponent_deck_archetypes").fetchall()
    }
    to_insert = [
        row for row in _ARCHETYPES_DATA
        if row[0].lower() not in existing_names
    ]
    if not to_insert:
        logger.info("opponent_deck_archetypes: tous les archetypes meta sont deja presents")
        return
    conn.executemany(
        "INSERT INTO opponent_deck_archetypes (name, key_pokemon, notes) VALUES (?,?,?)",
        to_insert,
    )
    logger.info("opponent_deck_archetypes: %d archetypes inseres (%d deja presents)",
                len(to_insert), len(existing_names))

_MIGRATIONS = {
    2: "ALTER TABLE matches ADD COLUMN notes TEXT",
    3: "ALTER TABLE matches ADD COLUMN tags TEXT",
    4: [
        "ALTER TABLE matches ADD COLUMN turns_played INTEGER",
        "ALTER TABLE matches ADD COLUMN player_points INTEGER",
        "ALTER TABLE matches ADD COLUMN opponent_points INTEGER",
    ],
    5: "ALTER TABLE matches ADD COLUMN damage_dealt INTEGER",
    6: "ALTER TABLE matches ADD COLUMN match_type TEXT",
    7: "ALTER TABLE matches ADD COLUMN energy_type TEXT",
    8: "ALTER TABLE matches ADD COLUMN conceded_by TEXT",
    9: [
        "ALTER TABLE matches ADD COLUMN rank_name TEXT",
        "ALTER TABLE matches ADD COLUMN rank_points INTEGER",
    ],
    10: "ALTER TABLE matches ADD COLUMN opponent_energy_type TEXT",
    11: "ALTER TABLE decks ADD COLUMN energy_type TEXT",
    12: "ALTER TABLE matches ADD COLUMN opponent_deck TEXT",
    13: "CREATE TABLE IF NOT EXISTS opponent_deck_archetypes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, key_pokemon TEXT NOT NULL, notes TEXT)",
    14: _seed_archetypes,
}

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
    raw_ocr_data TEXT,
    notes        TEXT,
    tags         TEXT
);
"""

_CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""

_CREATE_DECK_MAPPINGS = """
CREATE TABLE IF NOT EXISTS deck_detection_mappings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_name TEXT NOT NULL,
    energy_type   TEXT,
    deck_id       INTEGER REFERENCES decks(id) ON DELETE SET NULL,
    seen_count    INTEGER DEFAULT 1,
    confirmed     INTEGER DEFAULT 0
);
"""

_CREATE_OPPONENT_ARCHETYPES = """
CREATE TABLE IF NOT EXISTS opponent_deck_archetypes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    key_pokemon TEXT NOT NULL,
    notes       TEXT
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
            conn.execute(_CREATE_DECK_MAPPINGS)
            conn.execute(_CREATE_OPPONENT_ARCHETYPES)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)

            row = conn.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            else:
                current = row["version"]
                for v in sorted(_MIGRATIONS.keys()):
                    if v > current:
                        sqls = _MIGRATIONS[v]
                        # callable(conn) pour les migrations complexes (ex: seed data)
                        if callable(sqls):
                            try:
                                sqls(conn)
                                logger.info("Migration schema v%d (callable) appliquée", v)
                            except Exception as mig_e:
                                logger.warning("Migration v%d ignorée: %s", v, mig_e)
                        else:
                            if isinstance(sqls, str):
                                sqls = [sqls]
                            for sql in sqls:
                                try:
                                    conn.execute(sql)
                                    logger.info("Migration schema v%d appliquée: %s", v, sql)
                                except Exception as mig_e:
                                    logger.warning("Migration v%d ignorée: %s", v, mig_e)
                        conn.execute("UPDATE schema_version SET version = ?", (v,))
            # Seed archetypes meta à chaque démarrage (insère uniquement les manquants)
            try:
                _seed_archetypes(conn)
            except Exception as seed_e:
                logger.warning("Seed archetypes ignoré: %s", seed_e)

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
