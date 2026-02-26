"""tracker/capture/detector.py — Machine à états combat + boucle de polling MUMU.

CombatState : IDLE → PRE_QUEUE → IN_COMBAT → END_SCREEN → IDLE
StateDetector : détecte l'état du jeu depuis une capture PIL (stubs à calibrer).
PollingLoop : thread daemon 100ms — détecte MUMU + pilote les transitions d'état.
"""
import logging
import threading
from enum import Enum

from tracker.capture.screen import capture_region_pil, find_mumu_window

logger = logging.getLogger(__name__)


class CombatState(Enum):
    """États de la machine à états du pipeline de capture."""
    IDLE = "idle"
    PRE_QUEUE = "pre_queue"
    IN_COMBAT = "in_combat"
    END_SCREEN = "end_screen"


class StateDetector:
    """Détecte l'état du jeu Pokemon TCG Pocket depuis une image PIL.

    Les méthodes retournent False par défaut — stubs à calibrer sur Windows
    avec de vrais screenshots une fois MUMU configuré.

    Calibration :
    1. Capturer un screenshot de chaque état via api.capture_test_frame()
    2. Identifier les pixels/régions caractéristiques de chaque état
    3. Remplacer les stubs par des checks de couleur/template matching
    """

    def is_pre_queue_ranked(self, img) -> bool:
        """Détecte l'écran de file d'attente ranked (avant le combat).

        Indicateurs visuels Pokemon TCG Pocket :
        - Bouton "Battle!" ou icône ranked visible
        - Fond/disposition spécifique de l'écran de queue ranked

        TODO: Calibrer avec screenshot réel de l'écran pré-queue ranked.
        """
        return False

    def is_in_combat(self, img) -> bool:
        """Détecte que le combat est actuellement en cours.

        Indicateurs visuels Pokemon TCG Pocket :
        - Main de cartes visible en bas
        - Zone de jeu avec HP trackers
        - Interface de combat active

        TODO: Calibrer avec screenshot réel de l'écran de combat.
        """
        return False

    def is_end_screen(self, img) -> bool:
        """Détecte l'écran de résultat de fin de combat (WIN/LOSE).

        Indicateurs visuels Pokemon TCG Pocket :
        - Texte "WIN!" ou "LOSE!" (ou "DRAW")
        - Fond caractéristique de l'écran de résultat

        TODO: Calibrer avec screenshot réel de l'écran de fin.
        """
        return False


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
