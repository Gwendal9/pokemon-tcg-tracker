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
import warnings

# Supprime les UserWarnings verbeux de PyTorch (pin_memory sans GPU, etc.)
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

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
    from tracker.capture.screen import get_tracker_start_position  # noqa: PLC0415
    _tracker_w, _tracker_h = 900, 600
    _wx, _wy = get_tracker_start_position(_tracker_w, _tracker_h)
    window = webview.create_window(
        "Pokemon TCG Tracker",
        index_path,
        js_api=api,
        width=_tracker_w,
        height=_tracker_h,
        min_size=(_tracker_w, _tracker_h),
        x=_wx,
        y=_wy,
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
        prequeue_img          = None
        prequeue_data         = {}  # {match_type, deck_name, energy_type}
        pending_match         = None
        opponent_energy_type  = "?"
        _energy_stop          = None  # threading.Event pour stopper la détection énergie
        opponent_pokemon_seen = []   # noms Pokemon adverses vus pendant le combat

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
            close = _difflib.get_close_matches(deck_name, names, n=1, cutoff=0.4)
            if close:
                for d in decks:
                    if d["name"] == close[0]:
                        logger.info("Deck détecté (fuzzy): '%s' → '%s' (id=%s)",
                                    deck_name, d["name"], d["id"])
                        return d["id"]
        except Exception as e:
            logger.warning("_find_deck_id_by_name: %s", e)
        return fallback_id

    def on_state_changed(prev_state, new_state):
        config_data = api._config.get_all()
        region = config_data.get("mumu_region")
        if not region:
            return
        if new_state == CombatState.PRE_QUEUE:
            if ocr_state._energy_stop:
                ocr_state._energy_stop.set()
            ocr_state.opponent_pokemon_seen = []

            def _scan_prequeue(region):
                import time as _time
                # Réessayer jusqu'à 8x (toutes les 1.5s) jusqu'à obtenir deck + type + énergie
                for attempt in range(8):
                    _img = capture_region_pil(region)
                    if _img:
                        data = ocr_pipeline.extract_prequeue_data(_img)
                        deck_name   = data.get("deck_name", "?")
                        energy_type = data.get("energy_type", "?")
                        match_type  = data.get("match_type", "?")
                        ocr_state.prequeue_img  = _img
                        ocr_state.prequeue_data = data
                        logger.info(
                            "Prequeue scan #%d : type=%s deck=%s energy=%s",
                            attempt + 1, match_type, deck_name, energy_type,
                        )
                        got_deck   = deck_name and deck_name != "?"
                        got_energy = energy_type and energy_type != "?"
                        got_type   = match_type and match_type != "?"
                        if got_deck and got_energy and got_type:
                            break  # toutes les infos trouvées
                        if attempt < 7:
                            _time.sleep(1.5)
                # Enregistrer la détection dans la table mappings (non confirmé)
                deck_name   = ocr_state.prequeue_data.get("deck_name", "?")
                energy_type = ocr_state.prequeue_data.get("energy_type", "?")
                if deck_name and deck_name != "?":
                    try:
                        api._models.upsert_deck_detection(deck_name, energy_type)
                    except Exception as _e:
                        logger.warning("upsert_deck_detection: %s", _e)

            threading.Thread(target=_scan_prequeue, args=(region,), daemon=True).start()

        elif new_state == CombatState.IN_COMBAT:
            ocr_state.opponent_energy_type = "?"
            stop_event = threading.Event()
            ocr_state._energy_stop = stop_event

            def _detect_opponent_energy(stop_ev):
                import time as _time
                import os as _os
                from collections import Counter as _Counter
                from tracker.paths import get_data_dir as _get_data_dir  # noqa: PLC0415
                _region = config_data.get("mumu_region")
                if not _region:
                    return
                # Attendre la fin des animations d'entrée en combat
                _time.sleep(10)
                if stop_ev.is_set():
                    return
                counter = _Counter()
                consecutive = 0
                last_energy = None
                deadline = _time.monotonic() + 90  # fenêtre étendue à 90s
                while _time.monotonic() < deadline and not stop_ev.is_set():
                    _img = capture_region_pil(_region)
                    if _img is not None:
                        energy = ocr_pipeline.extract_opponent_energy(_img)
                        score = getattr(ocr_pipeline, "_last_energy_score", 0.0)
                        if energy and energy != "?":
                            counter[energy] += 1
                            ocr_state.opponent_energy_type = counter.most_common(1)[0][0]
                            # Sortie immédiate si score très élevé (icône clairement visible)
                            if score >= 0.45:
                                logger.info(
                                    "Energie adverse confirmee haute confiance (score=%.3f): %s",
                                    score, energy,
                                )
                                break
                            # Sortie anticipée : même énergie 3 fois consécutives
                            if energy == last_energy:
                                consecutive += 1
                                if consecutive >= 3:
                                    logger.info(
                                        "Energie adverse confirmee (%dx consecutif): %s",
                                        consecutive, energy,
                                    )
                                    break
                            else:
                                consecutive = 1
                                last_energy = energy
                        else:
                            consecutive = 0
                            last_energy = None
                    _time.sleep(1)
                if counter:
                    logger.info(
                        "Energie adverse finale: %s (votes: %s)",
                        ocr_state.opponent_energy_type, dict(counter),
                    )
                else:
                    logger.info("Energie adverse: aucune detection sur 90s")
                # Nettoyage des images debug
                for _fname in ("debug_opponent_energy.png", "debug_opponent_energy_crop.png"):
                    try:
                        _os.remove(_os.path.join(_get_data_dir(), _fname))
                    except FileNotFoundError:
                        pass

            threading.Thread(
                target=_detect_opponent_energy, args=(stop_event,), daemon=True
            ).start()

            def _detect_opponent_pokemon(stop_ev):
                import time as _time
                _region = config_data.get("mumu_region")
                if not _region:
                    return
                _time.sleep(5)  # attendre fin animations
                seen = []
                while not stop_ev.is_set():
                    _img = capture_region_pil(_region)
                    if _img is not None:
                        name = ocr_pipeline.extract_active_opponent_pokemon(_img)
                        if name and name not in seen:
                            seen.append(name)
                            ocr_state.opponent_pokemon_seen = list(seen)
                            logger.info("Pokemon adverse detecte: %s (total: %s)", name, seen)
                    _time.sleep(5)

            threading.Thread(
                target=_detect_opponent_pokemon, args=(stop_event,), daemon=True
            ).start()

        elif new_state == CombatState.END_SCREEN:
            if ocr_state._energy_stop:
                ocr_state._energy_stop.set()
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

                # Snapshot du résultat ML au moment de la transition (avant tout OCR)
                ml_outcome = polling.last_outcome

                try:
                    # Capture immédiate pour récupérer le résultat (écran carte star)
                    first_img = capture_region_pil(region)
                    try:
                        first_data = ocr_pipeline.extract_end_screen_data(first_img) if first_img else {}
                    except Exception as _e:
                        logger.warning("OCR first frame échoué: %s", _e)
                        first_data = {}
                    result_backup = first_data.get("result", "?")

                    # Polling jusqu'à l'écran de stats (max 90s, 0.15s entre captures)
                    # Sleep APRES la capture pour ne pas rater un écran fugace
                    match_data = None
                    stats_img = None
                    for _attempt in range(600):
                        img = capture_region_pil(region)
                        if img is None:
                            _time.sleep(0.15)
                            continue
                        try:
                            data = ocr_pipeline.extract_end_screen_data(img)
                        except Exception:
                            continue
                        raw = data.get("raw_ocr_data", "")
                        on_stats_screen = "tours jou" in raw.lower() or "ordre d" in raw.lower()
                        if data.get("turns_played") is not None or on_stats_screen:
                            match_data = data
                            stats_img = img
                            logger.info("Stats trouvées à la tentative %d", _attempt + 1)
                            break
                        _time.sleep(0.15)

                    if match_data is None:
                        logger.warning("Écran de stats non trouvé après 90s — utilisation données partielles")
                        match_data = first_data if first_data else {}

                    # Conserver le résultat du premier écran si le stats screen ne l'a pas
                    if match_data.get("result", "?") == "?":
                        match_data["result"] = result_backup

                except Exception as _global_e:
                    logger.error("_capture_end_screen OCR phase: %s", _global_e)
                    match_data = {}

                # Fallback ML si l'OCR n'a pas reconnu le résultat
                if match_data.get("result", "?") == "?":
                    if ml_outcome == "win":
                        match_data["result"] = "W"
                    elif ml_outcome == "lose":
                        match_data["result"] = "L"
                    logger.info("Résultat depuis ML fallback: %s", match_data.get("result"))

                match_data["deck_id"]      = deck_id
                match_data["match_type"]   = ocr_state.prequeue_data.get("match_type")
                match_data["energy_type"]  = ocr_state.prequeue_data.get("energy_type")
                match_data["rank_name"]           = ocr_state.prequeue_data.get("rank_name")
                match_data["rank_points"]         = ocr_state.prequeue_data.get("rank_points")
                match_data["opponent_energy_type"] = ocr_state.opponent_energy_type
                # Règle abandon (basée sur les points — un match normal se termine
                # toujours avec au moins 3 prix pour le vainqueur) :
                # - Victoire ET mes prix < 3  → adversaire a abandonné
                # - Défaite  ET ses prix < 3  → j'ai abandonné
                _player_pts = match_data.get("player_points")
                _opp_pts    = match_data.get("opponent_points")
                _result     = match_data.get("result")
                if _result == "W" and isinstance(_player_pts, int) and _player_pts < 3:
                    match_data["conceded_by"] = "opponent"
                    logger.info("Abandon adversaire déduit: victoire avec %d prix", _player_pts)
                elif _result == "L" and isinstance(_opp_pts, int) and _opp_pts < 3:
                    match_data["conceded_by"] = "self"
                    logger.info("Abandon joueur déduit: défaite avec adversaire à %d prix", _opp_pts)
                else:
                    match_data["conceded_by"] = None
                if not match_data.get("captured_at"):
                    from datetime import datetime as _dt
                    match_data["captured_at"] = _dt.now().isoformat()
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
                    _img_to_save = stats_img if stats_img is not None else first_img
                    if _img_to_save:
                        _debug_path = os.path.join(_data_dir, "debug_end_screen.png")
                        _img_to_save.save(_debug_path)
                        logger.info("Debug end screen sauvegardé: %s", _debug_path)
                except Exception as _e:
                    logger.debug("Debug save failed: %s", _e)

                try:
                    # Détection deck adverse avant sauvegarde
                    _best_deck = None
                    if ocr_state.opponent_pokemon_seen:
                        try:
                            _proposals = api._models.match_opponent_archetypes(
                                ocr_state.opponent_pokemon_seen
                            )
                            if _proposals:
                                _best_deck = _proposals[0]
                                match_data["opponent_deck"] = _best_deck["name"]
                                logger.info(
                                    "Deck adverse detecte: %s (score %d/%d) pokemon vus: %s",
                                    _best_deck["name"], _best_deck["score"],
                                    _best_deck["total"], ocr_state.opponent_pokemon_seen,
                                )
                        except Exception as _pe:
                            logger.debug("Deck detection pre-save error: %s", _pe)

                    with api._db_lock:
                        saved = api._models.save_match(match_data)
                    logger.info("Match enregistré: id=%d opponent_deck=%s",
                                saved["id"], match_data.get("opponent_deck"))
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

    # Reconnexion automatique à la fenêtre sauvegardée
    def _auto_reconnect_window():
        import time as _t
        _t.sleep(2)  # attendre que le bureau soit chargé
        try:
            from tracker.capture.screen import find_window_by_title  # noqa: PLC0415
            cfg = api._config.get_all()
            saved_title = cfg.get("window_title")
            if not saved_title:
                return
            region = find_window_by_title(saved_title)
            if region is None:
                logger.info("Fenêtre '%s' non trouvée au démarrage.", saved_title)
                return
            cfg["mumu_region"] = region
            api._config.save(cfg)
            logger.info("Fenêtre '%s' reconnectée automatiquement.", saved_title)
        except Exception as e:
            logger.warning("Auto-reconnexion fenêtre: %s", e)

    threading.Thread(target=_auto_reconnect_window, name="auto-reconnect", daemon=True).start()

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
