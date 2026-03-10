"""tracker/api/api.py — Bridge pywebview.

Toutes les méthodes sont des `def` synchrones.
pywebview 6.1 exécute les appels API dans un thread dédié — pas besoin d'async.
Les coroutines async causaient un RuntimeWarning "coroutine never awaited".

Règles critiques :
- Retourner {"error": "message"} en cas d'erreur (jamais lever d'exception non catchée)
- self._db_lock protège toutes les écritures SQLite depuis le thread de capture
- Les méthodes bridge conservent snake_case dans les dicts retournés (jamais camelCase)
"""
import concurrent.futures
import logging
import threading

from tracker.db.database import DatabaseManager
from tracker.db.models import Models
from tracker.config import ConfigManager
from tracker.capture.screen import (
    capture_region, capture_region_pil,
    select_region_interactive, auto_detect_mumu_region, show_region_highlight,
    list_all_windows, get_window_region,
)
from tracker.paths import get_data_dir

logger = logging.getLogger(__name__)


class TrackerAPI:
    """Bridge pywebview — toutes les méthodes sont synchrones (def)."""

    def __init__(self, db: DatabaseManager):
        self._db = db
        self._models = Models(db)
        self._db_lock = threading.Lock()
        self._config = ConfigManager()
        self._polling = None  # injecté depuis main.py via set_polling()
        logger.info("TrackerAPI initialisée")

    # -------------------------------------------------------------------------
    # Deck CRUD (Story 2.1)
    # -------------------------------------------------------------------------

    def get_decks(self) -> list:
        """Retourne la liste de tous les decks."""
        try:
            return self._models.get_decks()
        except Exception as e:
            logger.error("get_decks: %s", e)
            return {"error": str(e)}

    def create_deck(self, name: str) -> dict:
        """Crée un deck. Retourne {"error": ...} si le nom est vide."""
        if not name or not name.strip():
            return {"error": "Le nom du deck ne peut pas être vide"}
        try:
            return self._models.create_deck(name.strip())
        except Exception as e:
            logger.error("create_deck: %s", e)
            return {"error": str(e)}

    def update_deck(self, deck_id: int, name: str) -> bool:
        """Met à jour le nom d'un deck. Retourne True si succès."""
        try:
            return self._models.update_deck(deck_id, name.strip())
        except Exception as e:
            logger.error("update_deck: %s", e)
            return {"error": str(e)}

    def delete_deck(self, deck_id: int) -> bool:
        """Supprime un deck. Retourne True si succès, False si inexistant."""
        try:
            return self._models.delete_deck(deck_id)
        except Exception as e:
            logger.error("delete_deck: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Config (Story 2.2)
    # -------------------------------------------------------------------------

    def get_config(self) -> dict:
        """Retourne la configuration complète (config.json + defaults)."""
        try:
            return self._config.get_all()
        except Exception as e:
            logger.error("get_config: %s", e)
            return {"error": str(e)}

    def save_config(self, config: dict) -> bool:
        """Sauvegarde la configuration dans config.json."""
        try:
            return self._config.save(config)
        except Exception as e:
            logger.error("save_config: %s", e)
            return {"error": str(e)}

    def auto_detect_region(self) -> dict:
        """Détecte automatiquement la zone client MuMu et affiche un cadre rouge de confirmation.

        Utilise win32gui pour lire le rect client exact (sans barre de titre Windows).
        Le cadre rouge s'affiche 2,5 s dans un thread daemon pour ne pas bloquer.
        """
        try:
            region = auto_detect_mumu_region()
            if region is None:
                return {"error": "Fenêtre MuMu introuvable. Ouvrez MuMu Player et réessayez."}
            config = self._config.get_all()
            config["mumu_region"] = region
            self._config.save(config)
            import threading  # noqa: PLC0415
            threading.Thread(target=show_region_highlight, args=(region,), daemon=True).start()
            return {"ok": True, "region": region}
        except Exception as e:
            logger.error("auto_detect_region: %s", e)
            return {"error": str(e)}

    def list_windows(self) -> list:
        """Retourne toutes les fenêtres visibles pour sélection manuelle de la région."""
        try:
            return list_all_windows()
        except Exception as e:
            logger.error("list_windows: %s", e)
            return {"error": str(e)}

    def select_window_as_region(self, hwnd: int) -> dict:
        """Sélectionne une fenêtre par son hwnd comme région de capture et affiche le cadre rouge."""
        try:
            region = get_window_region(hwnd)
            if region is None:
                return {"error": "Impossible de récupérer les coordonnées de cette fenêtre."}
            config = self._config.get_all()
            config["mumu_region"] = region
            self._config.save(config)
            import threading  # noqa: PLC0415
            threading.Thread(target=show_region_highlight, args=(region,), daemon=True).start()
            return {"ok": True, "region": region}
        except Exception as e:
            logger.error("select_window_as_region: %s", e)
            return {"error": str(e)}

    def start_region_selection(self) -> dict:
        """Lance le sélecteur de région tkinter (overlay fullscreen).

        Méthode synchrone — bloque jusqu'à sélection ou annulation (max 120s).
        tkinter tourne dans un thread séparé pour ne pas conflictuer avec pywebview.
        Sauvegarde la région dans config.json si sélection valide.
        Windows-only — mockable en tests.
        """
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(select_region_interactive)
                region = future.result(timeout=120)
            if region is None:
                return {"error": "Sélection annulée"}
            config = self._config.get_all()
            config["mumu_region"] = region
            self._config.save(config)
            return {"ok": True, "region": region}
        except Exception as e:
            logger.error("start_region_selection: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Stats (Epic 4 — Story 4.1)
    # -------------------------------------------------------------------------

    def get_stats(self, season: str = None) -> dict:
        """Retourne les statistiques agrégées (winrate global + par deck)."""
        try:
            return self._models.get_stats(season=season)
        except Exception as e:
            logger.error("get_stats: %s", e)
            return {"error": str(e)}

    def update_match_field(self, match_id: int, field: str, value: str) -> bool:
        """Modifie un champ d'un match existant. Protégé par _db_lock."""
        try:
            with self._db_lock:
                return self._models.update_match_field(match_id, field, value)
        except Exception as e:
            logger.error("update_match_field: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Matches (Story 3.4)
    # -------------------------------------------------------------------------

    def delete_match(self, match_id: int) -> bool:
        """Supprime un match. Retourne True si succès, False si inexistant."""
        try:
            with self._db_lock:
                return self._models.delete_match(match_id)
        except Exception as e:
            logger.error("delete_match: %s", e)
            return {"error": str(e)}

    def save_match(self, match_data: dict) -> dict:
        """Enregistre un match capturé en DB. Protégé par _db_lock."""
        try:
            with self._db_lock:
                return self._models.save_match(match_data)
        except Exception as e:
            logger.error("save_match: %s", e)
            return {"error": str(e)}

    def get_seasons(self) -> list:
        """Retourne les saisons distinctes (non nulles) présentes dans la DB."""
        try:
            return self._models.get_seasons()
        except Exception as e:
            logger.error("get_seasons: %s", e)
            return {"error": str(e)}

    def get_matches(self, season: str = None, deck_id: int = None) -> list:
        """Retourne l'historique des matchs."""
        try:
            return self._models.get_matches(season=season, deck_id=deck_id)
        except Exception as e:
            logger.error("get_matches: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Capture status
    # -------------------------------------------------------------------------

    def set_polling(self, polling) -> None:
        """Injecte la référence au PollingLoop depuis main.py (Story 3.1)."""
        self._polling = polling

    def capture_test_frame(self) -> dict:
        """Capture un frame de la région configurée pour test visuel."""
        config = self._config.get_all()
        region = config.get("mumu_region")
        if not region:
            return {"error": "Aucune région configurée. Configurez d'abord la région MUMU."}
        frame = capture_region(region)
        if frame is None:
            return {"error": "Capture de la région échouée."}
        return frame

    def get_capture_status(self) -> dict:
        """Retourne l'état courant du pipeline de capture."""
        config = self._config.get_all()
        region = config.get("mumu_region")

        if self._polling is not None:
            return {
                "mumu_detected": self._polling.mumu_detected,
                "state": self._polling.state.value,
                "region_configured": region is not None,
            }

        mumu_detected = False
        try:
            import win32gui  # noqa: PLC0415
            hwnd = win32gui.FindWindow(None, "MuMu Player")
            mumu_detected = bool(hwnd)
        except Exception:
            pass

        return {
            "mumu_detected": mumu_detected,
            "state": "idle",
            "region_configured": region is not None,
        }

    # -------------------------------------------------------------------------
    # Statut du modèle ML
    # -------------------------------------------------------------------------

    def get_calibration_status(self) -> dict:
        """Retourne le statut du modèle ML de détection d'état."""
        try:
            if self._polling is None or self._polling._detector is None:
                return {"model_available": False}
            d = self._polling._detector
            return {"model_available": d.is_model_available()}
        except Exception as e:
            logger.error("get_calibration_status: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Test OCR — capture immédiate et retour des données extraites
    # -------------------------------------------------------------------------

    def test_ocr_now(self) -> dict:
        """Capture l'écran MuMu actuel et retourne les données OCR extraites."""
        try:
            from tracker.capture.ocr import OcrPipeline  # noqa: PLC0415
            import os as _os
            region = self._config.get_all().get("mumu_region")
            if not region:
                return {"error": "Région MuMu non configurée"}
            img = capture_region_pil(region)
            if img is None:
                return {"error": "Capture échouée"}
            # Sauvegarder les crops pour diagnostic
            data_dir = get_data_dir()
            img.save(_os.path.join(data_dir, "debug_full.png"))
            w, h = img.size
            top_crop = img.crop((0, 0, w, int(0.35 * h)))
            bot_crop = img.crop((0, int(0.67 * h), int(0.85 * w), int(0.95 * h)))
            top_crop.save(_os.path.join(data_dir, "debug_crop_top.png"))
            bot_crop.save(_os.path.join(data_dir, "debug_crop_bot.png"))
            logger.info("Crops sauvegardés dans %s", data_dir)
            ocr = OcrPipeline()
            data = ocr.extract_end_screen_data(img)
            logger.info("test_ocr_now: %s", data)
            return data
        except Exception as e:
            logger.error("test_ocr_now: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Sampling — capture automatique pour dataset de labélisation
    # -------------------------------------------------------------------------

    def start_sampling(self) -> dict:
        """Démarre la boucle de capture automatique sur changement visuel."""
        try:
            from tracker.capture.sampler import SamplingLoop  # noqa: PLC0415
            if getattr(self, "_sampler", None) and self._sampler.is_running:
                return {"error": "Sampling déjà en cours."}
            region = self._config.get_all().get("mumu_region")
            if not region:
                return {"error": "Aucune région configurée."}
            self._sampler = SamplingLoop(config=self._config)
            t = threading.Thread(target=self._sampler.start, daemon=True)
            t.start()
            return {"ok": True}
        except Exception as e:
            logger.error("start_sampling: %s", e)
            return {"error": str(e)}

    def stop_sampling(self) -> dict:
        """Arrête la boucle de capture automatique."""
        try:
            sampler = getattr(self, "_sampler", None)
            if sampler is None or not sampler.is_running:
                return {"error": "Sampling non démarré."}
            sampler.stop()
            return {"ok": True, "saved": sampler.saved_count}
        except Exception as e:
            logger.error("stop_sampling: %s", e)
            return {"error": str(e)}

    def get_sampling_status(self) -> dict:
        """Retourne l'état du sampler et le nombre de captures sauvegardées."""
        try:
            from tracker.capture.sampler import list_unlabeled  # noqa: PLC0415
            sampler = getattr(self, "_sampler", None)
            running = sampler is not None and sampler.is_running
            saved = sampler.saved_count if sampler else 0
            unlabeled = list_unlabeled()
            return {
                "running": running,
                "saved_this_session": saved,
                "unlabeled_count": len(unlabeled),
            }
        except Exception as e:
            logger.error("get_sampling_status: %s", e)
            return {"error": str(e)}

    def get_unlabeled_samples(self) -> list:
        """Retourne la liste des captures non labélisées avec leur label auto-détecté."""
        try:
            import base64, io  # noqa: PLC0415, E401
            from tracker.capture.sampler import list_unlabeled  # noqa: PLC0415
            samples = list_unlabeled()
            result = []
            for s in samples:
                try:
                    img = __import__("PIL.Image", fromlist=["Image"]).open(s["path"])
                    img.thumbnail((320, 240))
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=75)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    result.append({
                        "filename": s["filename"],
                        "auto_label": s["auto_label"],
                        "thumbnail": b64,
                    })
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.error("get_unlabeled_samples: %s", e)
            return {"error": str(e)}

    def capture_now(self) -> dict:
        """Capture immédiatement l'écran et sauvegarde dans unlabeled/ pour labélisation."""
        try:
            from tracker.capture.sampler import capture_now  # noqa: PLC0415
            return capture_now(self._config)
        except Exception as e:
            logger.error("capture_now: %s", e)
            return {"error": str(e)}

    def label_sample(self, filename: str, label: str) -> dict:
        """Labélise une capture et la déplace dans le bon dossier."""
        try:
            from tracker.capture.sampler import label_sample  # noqa: PLC0415
            ok = label_sample(filename, label)
            return {"ok": ok}
        except Exception as e:
            logger.error("label_sample: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Test détection deck depuis l'écran actuel
    # -------------------------------------------------------------------------

    def test_deck_detection(self) -> dict:
        """Capture l'écran actuel et retourne la détection du deck (nom + énergie)."""
        try:
            from tracker.capture.ocr import OcrPipeline  # noqa: PLC0415
            region = self._config.get_all().get("mumu_region")
            if not region:
                return {"error": "Région non configurée"}
            img = capture_region_pil(region)
            if img is None:
                return {"error": "Capture échouée"}
            ocr = OcrPipeline()
            data = ocr.extract_prequeue_data(img)
            return data
        except Exception as e:
            logger.error("test_deck_detection: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Deck detection mappings
    # -------------------------------------------------------------------------

    def get_deck_mappings(self) -> list:
        """Retourne tous les mappings de détection de deck."""
        try:
            return self._models.get_deck_mappings()
        except Exception as e:
            logger.error("get_deck_mappings: %s", e)
            return {"error": str(e)}

    def save_deck_mapping(self, mapping_id: int, deck_id: int) -> dict:
        """Confirme un mapping : associe deck_id à une détection."""
        try:
            ok = self._models.save_deck_mapping(mapping_id, deck_id)
            return {"ok": ok}
        except Exception as e:
            logger.error("save_deck_mapping: %s", e)
            return {"error": str(e)}

    def delete_deck_mapping(self, mapping_id: int) -> dict:
        """Supprime un mapping de détection."""
        try:
            ok = self._models.delete_deck_mapping(mapping_id)
            return {"ok": ok}
        except Exception as e:
            logger.error("delete_deck_mapping: %s", e)
            return {"error": str(e)}

    def mark_match_conceded(self, match_id: int) -> dict:
        """Bascule le flag conceded_by='self' sur un match (toggle)."""
        try:
            with self._db_lock:
                matches = self._models.get_matches()
                m = next((x for x in matches if x["id"] == match_id), None)
                if m is None:
                    return {"error": "Match introuvable"}
                current = m.get("conceded_by")
                new_val = None if current == "self" else "self"
                self._models.update_match_field(match_id, "conceded_by", new_val)
            return {"ok": True, "conceded_by": new_val}
        except Exception as e:
            logger.error("mark_match_conceded: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Export CSV
    # -------------------------------------------------------------------------

    def open_external_url(self, url: str) -> dict:
        """Ouvre une URL dans le navigateur par défaut."""
        import webbrowser
        try:
            webbrowser.open(url)
            return {"ok": True}
        except Exception as e:
            logger.error("open_external_url: %s", e)
            return {"error": str(e)}

    def export_matches_csv(self) -> dict:
        """Exporte tous les matchs en CSV dans data/matches_export.csv et l'ouvre."""
        import csv
        import os as _os
        try:
            matches = self._models.get_matches()
            decks = {d["id"]: d["name"] for d in self._models.get_decks()}
            data_dir = get_data_dir()
            _os.makedirs(data_dir, exist_ok=True)
            csv_path = _os.path.join(data_dir, "matches_export.csv")
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Résultat", "Deck", "Adversaire", "Premier", "Saison"])
                for m in matches:
                    writer.writerow([
                        m.get("captured_at", ""),
                        m.get("result", ""),
                        decks.get(m.get("deck_id"), ""),
                        m.get("opponent", ""),
                        m.get("first_player", ""),
                        m.get("season", ""),
                    ])
            _os.startfile(_os.path.abspath(csv_path))
            return {"ok": True, "path": csv_path}
        except Exception as e:
            logger.error("export_matches_csv: %s", e)
            return {"error": str(e)}
