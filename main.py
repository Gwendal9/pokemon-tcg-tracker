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
from tracker.backup import backup_db
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

    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def main() -> None:
    """Démarre l'application pokemon-tcg-tracker."""
    setup_logging()
    logger.info("Démarrage de pokemon-tcg-tracker")

    # Backup DB avant initialisation (silencieux si DB absente)
    _data_dir = get_data_dir()
    backup_db(
        db_path=os.path.join(_data_dir, "tracker.db"),
        data_dir=_data_dir,
    )

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

    import difflib as _difflib

    class _OcrState:
        prequeue_img        = None
        prequeue_data       = {}  # {match_type, deck_name, energy_type}
        pending_match       = None
        opponent_conceded   = False
        _abandon_watch_stop = None  # threading.Event pour stopper le watcher

    ocr_state = _OcrState()

    def _find_deck_id_by_name(deck_name: str, energy_type: str, fallback_id) -> int | None:
        """Cherche le deck_id pour une détection de deck.

        Priorité :
        1. Mapping confirmé en DB (detected_name + energy_type).
        2. Correspondance floue sur le nom (difflib).
        3. fallback_id (deck actif dans la config).
        """
        if not deck_name or deck_name == "?":
            return fallback_id
        try:
            # 1. Mapping confirmé
            mapped_id = api._models.find_deck_by_detection(deck_name, energy_type or "?")
            if mapped_id is not None:
                logger.info("Deck via mapping confirmé: '%s' → id=%s", deck_name, mapped_id)
                return mapped_id
            # 2. Correspondance floue
            decks = api._models.get_decks()
            names = [d["name"] for d in decks]
            close = _difflib.get_close_matches(deck_name, names, n=1, cutoff=0.5)
            if close:
                for d in decks:
                    if d["name"] == close[0]:
                        logger.info("Deck détecté (fuzzy): '%s' → '%s' (id=%s)",
                                    deck_name, d["name"], d["id"])
                        return d["id"]
        except Exception as e:
            logger.warning("_find_deck_id_by_name: %s", e)
        return fallback_id

    def _watch_for_abandon(stop_event):
        """Thread : détecte 'Votre adversaire a abandonné' pendant IN_COMBAT."""
        import time as _time
        import numpy as np  # noqa: PLC0415
        while not stop_event.is_set():
            _time.sleep(2)
            if polling.state != CombatState.IN_COMBAT:
                break
            region = api._config.get_all().get("mumu_region")
            if not region:
                continue
            img = capture_region_pil(region)
            if img is None:
                continue
            try:
                w, h = img.size
                # Vérification rapide : zone centrale très blanche = dialogue overlay
                center = img.crop((int(0.1*w), int(0.3*h), int(0.9*w), int(0.7*h)))
                arr = np.asarray(center.convert("L"), dtype=float) / 255.
                if arr.mean() < 0.80:
                    continue
                # Confirmation OCR : chercher "abandonné"
                results = ocr_pipeline._read_text(center)
                text = " ".join(t for (_, t, c) in results if c > 0.35).lower()
                if "abandonn" in text:
                    ocr_state.opponent_conceded = True
                    logger.info("Abandon adversaire confirmé par OCR")
                    break
            except Exception as e:
                logger.debug("_watch_for_abandon tick: %s", e)

    def on_state_changed(prev_state, new_state):
        config_data = api._config.get_all()
        region = config_data.get("mumu_region")
        if not region:
            return
        if new_state == CombatState.PRE_QUEUE:
            ocr_state.opponent_conceded = False
            if ocr_state._abandon_watch_stop:
                ocr_state._abandon_watch_stop.set()
            ocr_state.prequeue_img = capture_region_pil(region)
            if ocr_state.prequeue_img:
                ocr_state.prequeue_data = ocr_pipeline.extract_prequeue_data(ocr_state.prequeue_img)
            # Enregistrer la détection dans la table mappings (non confirmé)
            deck_name   = ocr_state.prequeue_data.get("deck_name", "?")
            energy_type = ocr_state.prequeue_data.get("energy_type", "?")
            if deck_name and deck_name != "?":
                try:
                    api._models.upsert_deck_detection(deck_name, energy_type)
                except Exception as _e:
                    logger.warning("upsert_deck_detection: %s", _e)
        elif new_state == CombatState.IN_COMBAT:
            stop_event = threading.Event()
            ocr_state._abandon_watch_stop = stop_event
            threading.Thread(target=_watch_for_abandon, args=(stop_event,), daemon=True).start()
        elif new_state == CombatState.END_SCREEN:
            if ocr_state._abandon_watch_stop:
                ocr_state._abandon_watch_stop.set()
            active_deck_id = config_data.get("active_deck_id")
            deck_id = _find_deck_id_by_name(
                ocr_state.prequeue_data.get("deck_name"),
                ocr_state.prequeue_data.get("energy_type", "?"),
                active_deck_id,
            )
            # L'écran de stats n'apparaît qu'après le clic sur "Touchez pour continuer"
            # On lance la capture dans un thread séparé pour ne pas bloquer le polling
            def _capture_end_screen(region, deck_id):
                import time as _time

                # Capture immédiate pour récupérer le résultat (écran carte star)
                first_img = capture_region_pil(region)
                first_data = ocr_pipeline.extract_end_screen_data(first_img) if first_img else {}
                result_backup = first_data.get("result", "?")

                # Polling jusqu'à l'écran de stats (max 90s — attend le clic utilisateur)
                match_data = None
                stats_img = None
                for _attempt in range(180):
                    _time.sleep(0.5)
                    img = capture_region_pil(region)
                    if img is None:
                        continue
                    data = ocr_pipeline.extract_end_screen_data(img)
                    raw = data.get("raw_ocr_data", "")
                    on_stats_screen = "tours jou" in raw.lower() or "ordre d" in raw.lower()
                    if data.get("turns_played") is not None or on_stats_screen:
                        match_data = data
                        stats_img = img
                        logger.info("Stats trouvées à la tentative %d", _attempt + 1)
                        break

                if match_data is None:
                    logger.warning("Écran de stats non trouvé après 90s — utilisation données partielles")
                    match_data = first_data

                # Conserver le résultat du premier écran si le stats screen ne l'a pas
                if match_data.get("result") == "?":
                    match_data["result"] = result_backup

                # Fallback ML si l'OCR n'a pas reconnu le résultat
                if match_data.get("result") == "?":
                    ml_outcome = polling.last_outcome
                    if ml_outcome == "win":
                        match_data["result"] = "W"
                    elif ml_outcome == "lose":
                        match_data["result"] = "L"

                match_data["deck_id"]      = deck_id
                match_data["match_type"]   = ocr_state.prequeue_data.get("match_type")
                match_data["energy_type"]  = ocr_state.prequeue_data.get("energy_type")
                match_data["conceded_by"]  = "opponent" if ocr_state.opponent_conceded else None
                logger.info(
                    "Match OCR extrait: result=%s opponent=%s first=%s turns=%s pts=%s/%s dmg=%s",
                    match_data.get("result"),
                    match_data.get("opponent"),
                    match_data.get("first_player"),
                    match_data.get("turns_played"),
                    match_data.get("player_points"),
                    match_data.get("opponent_points"),
                    match_data.get("damage_dealt"),
                )

                # Debug: sauvegarder l'image de stats pour analyse
                try:
                    _img_to_save = stats_img or first_img
                    if _img_to_save:
                        _debug_path = os.path.join(_data_dir, "debug_end_screen.png")
                        _img_to_save.save(_debug_path)
                        logger.info("Debug end screen sauvegardé: %s", _debug_path)
                except Exception as _e:
                    logger.debug("Debug save failed: %s", _e)

                try:
                    with api._db_lock:
                        saved = api._models.save_match(match_data)
                    logger.info("Match enregistré: id=%d", saved["id"])
                    window.evaluate_js(
                        "window.dispatchEvent(new CustomEvent('match-created',{detail:{auto:true}}))"
                    )
                    try:
                        from plyer import notification
                        notification.notify(
                            title="Pokemon TCG Tracker",
                            message="Match enregistré : " + str(saved.get("result", "?")),
                            app_name="Pokemon TCG Tracker",
                            timeout=4,
                        )
                    except Exception:
                        pass
                except Exception as e:
                    logger.error("Enregistrement match échoué: %s", e)

            threading.Thread(
                target=_capture_end_screen,
                args=(region, deck_id),
                daemon=True,
            ).start()

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
