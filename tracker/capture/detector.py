"""tracker/capture/detector.py — Machine à états combat + boucle de polling MUMU.

CombatState : IDLE → PRE_QUEUE → IN_COMBAT → END_SCREEN → IDLE
StateDetector : détecte l'état du jeu depuis une capture PIL.
PollingLoop : thread daemon 100ms — détecte MUMU + pilote les transitions d'état.
"""
import logging
import os
import threading
from enum import Enum

from PIL import Image

from tracker.capture.screen import capture_region_pil, find_mumu_window
from tracker.paths import get_data_dir

logger = logging.getLogger(__name__)

_CAL_DIR = os.path.join(get_data_dir(), "calibration")
_REF_PATHS = {
    "pre_queue":  os.path.join(_CAL_DIR, "pre_queue.png"),
    "in_combat":  os.path.join(_CAL_DIR, "in_combat.png"),
    "end_screen": os.path.join(_CAL_DIR, "end_screen.png"),
}

# Seuil MSE — valeur basse = images similaires. À ajuster si trop sensible.
_MSE_THRESHOLD = 2000.0


class CombatState(Enum):
    """États de la machine à états du pipeline de capture."""
    IDLE = "idle"
    PRE_QUEUE = "pre_queue"
    IN_COMBAT = "in_combat"
    END_SCREEN = "end_screen"


class StateDetector:
    """Détecte l'état du jeu Pokemon TCG Pocket depuis une image PIL.

    Calibration :
    1. Lancer le jeu dans l'état voulu
    2. Appeler calibrate(state_name, img) pour sauvegarder l'image de référence
    3. Les détections suivantes comparent par MSE l'image capturée à la référence

    Sans calibration (pas de fichier PNG de référence), toutes les méthodes
    retournent False — aucune transition ne peut avoir lieu.
    """

    def __init__(self):
        self._refs = {}  # cache {state_name: Image.Image ou None}

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, state_name: str, img) -> bool:
        """Sauvegarde img comme référence pour state_name.

        Args:
            state_name: 'pre_queue', 'in_combat' ou 'end_screen'.
            img: PIL Image capturée dans cet état.

        Returns:
            True si sauvegardé, False si state_name invalide ou erreur I/O.
        """
        if state_name not in _REF_PATHS:
            logger.warning("calibrate: état inconnu '%s'", state_name)
            return False
        os.makedirs(_CAL_DIR, exist_ok=True)
        try:
            img.convert("RGB").save(_REF_PATHS[state_name])
            self._refs.pop(state_name, None)  # invalider le cache
            logger.info("Calibration sauvegardée : %s → %s", state_name, _REF_PATHS[state_name])
            return True
        except Exception as e:
            logger.error("calibrate %s: %s", state_name, e)
            return False

    def is_calibrated(self, state_name: str) -> bool:
        """Retourne True si un fichier de référence existe pour state_name."""
        return os.path.exists(_REF_PATHS.get(state_name, ""))

    # ------------------------------------------------------------------
    # Détection (MSE contre référence calibrée)
    # ------------------------------------------------------------------

    def is_pre_queue_ranked(self, img) -> bool:
        """Détecte l'écran de file d'attente ranked."""
        ref = self._load_ref("pre_queue")
        if ref is None:
            return False
        return self._compare(img, ref) < _MSE_THRESHOLD

    def is_in_combat(self, img) -> bool:
        """Détecte que le combat est actuellement en cours."""
        ref = self._load_ref("in_combat")
        if ref is None:
            return False
        return self._compare(img, ref) < _MSE_THRESHOLD

    def is_end_screen(self, img) -> bool:
        """Détecte l'écran de résultat de fin de combat (WIN/LOSE)."""
        ref = self._load_ref("end_screen")
        if ref is None:
            return False
        return self._compare(img, ref) < _MSE_THRESHOLD

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _load_ref(self, state_name):
        """Charge et met en cache l'image de référence (lazy)."""
        if state_name not in self._refs:
            path = _REF_PATHS.get(state_name, "")
            if os.path.exists(path):
                try:
                    self._refs[state_name] = Image.open(path).convert("RGB")
                except Exception as e:
                    logger.error("_load_ref %s: %s", state_name, e)
                    self._refs[state_name] = None
            else:
                self._refs[state_name] = None
        return self._refs[state_name]

    def _compare(self, img, ref_img) -> float:
        """MSE pixel-par-pixel entre img et ref_img. Valeur basse = similaire."""
        try:
            import numpy as np  # noqa: PLC0415 — lazy import (disponible via easyocr)
            target = img.convert("RGB").resize(ref_img.size, Image.LANCZOS)
            arr1 = np.asarray(target, dtype=float)
            arr2 = np.asarray(ref_img, dtype=float)
            return float(np.mean((arr1 - arr2) ** 2))
        except Exception:
            return float("inf")


class PollingLoop:
    """Boucle de polling à 100ms — détecte MUMU et pilote la machine à états.

    Usage :
        detector = StateDetector()
        polling = PollingLoop(config=config_manager, detector=detector)
        polling.set_callbacks(on_mumu_detected=tray.set_state_active,
                              on_mumu_lost=tray.set_state_inactive,
                              on_state_changed=handle_state_change)
        thread = threading.Thread(target=polling.start, daemon=True)
        thread.start()
    """

    def __init__(self, interval: float = 0.1, config=None, detector=None):
        """
        Args:
            interval: Intervalle de polling en secondes (défaut 100ms).
            config: ConfigManager pour lire mumu_region. Si None, détection d'état désactivée.
            detector: StateDetector pour analyser les frames. Si None, détection d'état désactivée.
        """
        self._interval = interval
        self._config = config
        self._detector = detector
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state = CombatState.IDLE
        self._mumu_detected = False
        self._on_mumu_detected = None
        self._on_mumu_lost = None
        self._on_state_changed = None

    # ------------------------------------------------------------------
    # Propriétés thread-safe
    # ------------------------------------------------------------------

    @property
    def state(self) -> CombatState:
        with self._lock:
            return self._state

    @property
    def mumu_detected(self) -> bool:
        with self._lock:
            return self._mumu_detected

    # ------------------------------------------------------------------
    # Configuration & cycle de vie
    # ------------------------------------------------------------------

    def set_callbacks(self, on_mumu_detected=None, on_mumu_lost=None,
                      on_state_changed=None):
        """Enregistre les callbacks pour les transitions."""
        self._on_mumu_detected = on_mumu_detected
        self._on_mumu_lost = on_mumu_lost
        self._on_state_changed = on_state_changed

    def start(self):
        """Démarre la boucle de polling (bloquant — appeler depuis un thread dédié)."""
        self._stop_event.clear()
        logger.info("PollingLoop démarrée (interval=%.3fs)", self._interval)
        self._loop()

    def stop(self):
        """Arrête la boucle de polling (thread-safe)."""
        self._stop_event.set()
        logger.info("PollingLoop arrêtée")

    # ------------------------------------------------------------------
    # Boucle interne
    # ------------------------------------------------------------------

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error("polling error: %s", e)
            self._stop_event.wait(self._interval)

    def _tick(self):
        """Un cycle de polling : détecte MUMU, transitions callbacks, analyse état."""
        hwnd = find_mumu_window()
        on_detected = None
        on_lost = None

        with self._lock:
            prev = self._mumu_detected
            self._mumu_detected = bool(hwnd)
            if self._mumu_detected and not prev:
                logger.info("MUMU Player détecté (hwnd=%s)", hwnd)
                on_detected = self._on_mumu_detected
            elif not self._mumu_detected and prev:
                logger.info("MUMU Player perdu")
                self._state = CombatState.IDLE
                on_lost = self._on_mumu_lost

        # Callbacks hors du lock
        if on_detected:
            on_detected()
        if on_lost:
            on_lost()

        # Détection d'état (uniquement si MUMU présent + config + detector injectés)
        if self._mumu_detected and self._config is not None and self._detector is not None:
            self._detect_and_transition()

    def _detect_and_transition(self):
        """Capture un frame et détermine le prochain état via StateDetector."""
        region = self._config.get_all().get("mumu_region")
        if not region:
            return

        img = capture_region_pil(region)
        if img is None:
            return

        current = self.state
        try:
            next_state = self._compute_next_state(current, img)
        except Exception as e:
            logger.error("state detection error: %s", e)
            return

        if next_state != current:
            with self._lock:
                prev_state = self._state
                self._state = next_state
            logger.info("État → %s (était %s)", next_state.value, prev_state.value)
            if self._on_state_changed:
                self._on_state_changed(prev_state, next_state)

    def _compute_next_state(self, current: CombatState, img) -> CombatState:
        """Applique les règles de transition de la machine à états.

        Règles :
          IDLE       + is_pre_queue_ranked → PRE_QUEUE
          PRE_QUEUE  + is_in_combat        → IN_COMBAT
          PRE_QUEUE  + !is_pre_queue_ranked → IDLE   (a quitté la queue)
          IN_COMBAT  + is_end_screen       → END_SCREEN
          END_SCREEN + !is_end_screen      → IDLE
        """
        d = self._detector

        if current == CombatState.IDLE:
            if d.is_pre_queue_ranked(img):
                return CombatState.PRE_QUEUE

        elif current == CombatState.PRE_QUEUE:
            if d.is_in_combat(img):
                return CombatState.IN_COMBAT
            elif not d.is_pre_queue_ranked(img):
                return CombatState.IDLE

        elif current == CombatState.IN_COMBAT:
            if d.is_end_screen(img):
                return CombatState.END_SCREEN

        elif current == CombatState.END_SCREEN:
            if not d.is_end_screen(img):
                return CombatState.IDLE

        return current
