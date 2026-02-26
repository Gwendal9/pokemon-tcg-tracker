"""main.py — Point d'entrée de pokemon-tcg-tracker.

Orchestre :
- Logging (RotatingFileHandler)
- Base de données SQLite (DatabaseManager)
- Bridge API pywebview (TrackerAPI)
- Fenêtre dashboard pywebview (hide on close)
- Icône system tray pystray (daemon thread)
- Boucle polling MUMU 100ms (daemon thread)

Threading :
- Thread principal : webview.start()   — boucle GUI pywebview
- Thread daemon   : tray.run()         — boucle GUI pystray
- Thread daemon   : polling.start()    — polling MUMU 100ms
"""
import logging
import logging.handlers
import os
import threading

import webview

from tracker.api.api import TrackerAPI
from tracker.capture.detector import CombatState, PollingLoop, StateDetector
from tracker.capture.ocr import OcrPipeline
from tracker.capture.screen import capture_region_pil
from tracker.db.database import DatabaseManager
from tracker.paths import get_data_dir
from tracker.tray import TrayManager

_HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(get_data_dir(), "app.log")

logger = logging.getLogger(__name__)


def setup_logging(log_path: str = None) -> None:
    """Configure le logging applicatif avec RotatingFileHandler.

    Args:
        log_path: Chemin du fichier log. Par défaut : data/app.log.
                  Paramètre optionnel principalement pour les tests.
    """
    if log_path is None:
        log_path = LOG_PATH

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    level = logging.DEBUG if os.environ.get("PTCG_DEBUG") else logging.INFO

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    ))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


def main() -> None:
    """Démarre l'application pokemon-tcg-tracker."""
    setup_logging()
    logger.info("Démarrage de pokemon-tcg-tracker")

    # Initialisation DB et API bridge
    db = DatabaseManager()
    api = TrackerAPI(db)

    # Fenêtre pywebview
    index_path = os.path.join(_HERE, "ui", "index.html")
    window = webview.create_window(
        "Pokemon TCG Tracker",
        index_path,
        js_api=api,
        width=900,
        height=600,
        min_size=(900, 600),
    )

    # Fermeture fenêtre = hide (pas quit) — AC4
    def on_closing():
        window.hide()
        return False  # empêche la fermeture effective

    window.events.closing += on_closing

    # Callbacks tray
    def open_dashboard():
        window.show()

    def quit_app():
        logger.info("Arrêt demandé depuis le tray")
        tray.stop()
        window.destroy()

    # Tray dans un daemon thread
    tray = TrayManager(on_open_dashboard=open_dashboard, on_quit=quit_app)
    tray_thread = threading.Thread(target=tray.run, name="tray", daemon=True)
    tray_thread.start()

    # OCR pipeline + état partagé (Story 3.3)
    ocr_pipeline = OcrPipeline()

    class _OcrState:
        prequeue_img = None
        pending_match = None

    ocr_state = _OcrState()

    def on_state_changed(prev_state, new_state):
        config_data = api._config.get_all()
        region = config_data.get("mumu_region")
        if not region:
            return
        if new_state == CombatState.PRE_QUEUE:
            ocr_state.prequeue_img = capture_region_pil(region)
        elif new_state == CombatState.END_SCREEN:
            end_img = capture_region_pil(region)
            if end_img is None:
                return
            active_deck_id = config_data.get("active_deck_id")
            deck_id = ocr_pipeline.extract_deck_from_prequeue(
                ocr_state.prequeue_img, active_deck_id
            )
            match_data = ocr_pipeline.extract_end_screen_data(end_img)
            match_data["deck_id"] = deck_id
            ocr_state.pending_match = match_data
            logger.info("Match OCR extrait: result=%s", match_data.get("result"))
            try:
                with api._db_lock:
                    saved = api._models.save_match(ocr_state.pending_match)
                logger.info("Match enregistré: id=%d", saved["id"])
                ocr_state.pending_match = None
                window.evaluate_js(
                    "window.dispatchEvent(new CustomEvent('match-created',{detail:{auto:true}}))"
                )
            except Exception as e:
                logger.error("Enregistrement match échoué: %s", e)

    # Polling MUMU 100ms + détection états combat (Stories 3.1, 3.2)
    detector = StateDetector()
    polling = PollingLoop(interval=0.1, config=api._config, detector=detector)
    polling.set_callbacks(
        on_mumu_detected=tray.set_state_active,
        on_mumu_lost=tray.set_state_inactive,
        on_state_changed=on_state_changed,
    )
    api.set_polling(polling)
    polling_thread = threading.Thread(target=polling.start, name="polling", daemon=True)
    polling_thread.start()

    # Background update check (Story 5.1)
    def _check_update():
        import time as _time
        _time.sleep(8)  # attendre que l'UI soit chargée
        from tracker.version import __version__
        from tracker import updater
        result = updater.check_for_update(__version__)
        if result:
            version = str(result["version"]).replace("'", "").replace('"', '')
            url     = str(result["url"]).replace("'", "").replace('"', '')
            js = (
                "window.dispatchEvent(new CustomEvent('update-available',"
                "{{detail:{{version:'{v}',url:'{u}'}}}}))".format(v=version, u=url)
            )
            try:
                window.evaluate_js(js)
            except Exception:
                pass

    update_thread = threading.Thread(target=_check_update, name="updater", daemon=True)
    update_thread.start()

    # Boucle GUI pywebview (bloquant jusqu'à window.destroy())
    webview.start()
    logger.info("Application fermée proprement")


if __name__ == "__main__":
    main()
