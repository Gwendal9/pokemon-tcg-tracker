"""tracker/capture/detector.py — Machine à états combat + boucle de polling MUMU.

CombatState : IDLE → PRE_QUEUE → IN_COMBAT → END_SCREEN → IDLE

StateDetector : utilise le modèle ML (data/state_classifier.pkl) pour détecter
l'état du jeu. Fallback sur "unknown" si le modèle est absent.

PollingLoop : thread daemon 100ms — détecte MUMU + pilote les transitions d'état.
Expose last_outcome ("win" | "lose" | None) après une transition vers END_SCREEN.
"""
import logging
import os
import pickle
import threading
from enum import Enum

import numpy as np
from PIL import Image

from tracker.capture.screen import capture_region_pil, find_mumu_window
from tracker.paths import get_data_dir, get_project_root

logger = logging.getLogger(__name__)

# Cherche d'abord dans models/ (distribué avec le repo), puis dans data/ (local)
_MODEL_PATH = os.path.join(get_project_root(), "models", "state_classifier.pkl")
_MODEL_PATH_LEGACY = os.path.join(get_data_dir(), "state_classifier.pkl")
_IMG_SIZE = (160, 120)


# ---------------------------------------------------------------------------
# Features (dupliquées ici pour éviter une dépendance circulaire avec sampler)
# ---------------------------------------------------------------------------

def _extract_features(img: Image.Image) -> np.ndarray:
    from skimage.feature import hog  # noqa: PLC0415

    img_rgb = img.convert("RGB").resize(_IMG_SIZE, Image.LANCZOS)
    arr = np.asarray(img_rgb, dtype=np.uint8)

    gray = np.asarray(img_rgb.convert("L"), dtype=np.uint8)
    hog_feat = hog(
        gray,
        orientations=8,
        pixels_per_cell=(16, 16),
        cells_per_block=(2, 2),
        feature_vector=True,
    )

    hsv = _rgb_to_hsv(arr)
    hist_feats = []
    for ch in range(3):
        h, _ = np.histogram(hsv[:, :, ch], bins=16, range=(0, 1))
        hist_feats.append(h / (h.sum() + 1e-6))

    return np.concatenate([hog_feat, np.concatenate(hist_feats)])


def _rgb_to_hsv(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[:, :, 0] / 255., arr[:, :, 1] / 255., arr[:, :, 2] / 255.
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    h = np.zeros_like(r)
    s = np.where(cmax > 0, delta / cmax, 0.)
    v = cmax
    mr = (delta > 0) & (cmax == r)
    mg = (delta > 0) & (cmax == g)
    mb = (delta > 0) & (cmax == b)
    h[mr] = ((g[mr] - b[mr]) / delta[mr]) % 6
    h[mg] = (b[mg] - r[mg]) / delta[mg] + 2
    h[mb] = (r[mb] - g[mb]) / delta[mb] + 4
    h /= 6.
    return np.stack([h, s, v], axis=2)


def _crop_roi(img: Image.Image, roi: tuple) -> Image.Image:
    w, h = img.size
    return img.crop((
        int(roi[0] * w), int(roi[1] * h),
        int((roi[0] + roi[2]) * w), int((roi[1] + roi[3]) * h),
    ))


# ---------------------------------------------------------------------------
# CombatState
# ---------------------------------------------------------------------------

class CombatState(Enum):
    IDLE = "idle"
    PRE_QUEUE = "pre_queue"
    IN_COMBAT = "in_combat"
    END_SCREEN = "end_screen"


# ---------------------------------------------------------------------------
# StateDetector
# ---------------------------------------------------------------------------

class StateDetector:
    """Détecte l'état du jeu Pokemon TCG Pocket depuis une image PIL.

    Utilise le modèle SVM entraîné (state_classifier.pkl).
    Si le modèle est absent, toutes les méthodes retournent False.
    """

    def __init__(self):
        self._model = None        # chargé lazily
        self._model_loaded = False

    # ------------------------------------------------------------------
    # Modèle
    # ------------------------------------------------------------------

    def _load_model(self) -> dict | None:
        if self._model_loaded:
            return self._model
        self._model_loaded = True
        path = _MODEL_PATH if os.path.exists(_MODEL_PATH) else _MODEL_PATH_LEGACY
        if not os.path.exists(path):
            logger.warning("Modèle ML absent — détection désactivée.")
            return None
        try:
            with open(path, "rb") as f:
                self._model = pickle.load(f)
            logger.info("Modèle ML chargé : %s", path)
        except Exception as e:
            logger.error("Erreur chargement modèle : %s", e)
        return self._model

    def is_model_available(self) -> bool:
        return os.path.exists(_MODEL_PATH) or os.path.exists(_MODEL_PATH_LEGACY)

    def reload_model(self):
        """Force le rechargement du modèle (utile après un réentraînement)."""
        self._model = None
        self._model_loaded = False

    # ------------------------------------------------------------------
    # Prédiction
    # ------------------------------------------------------------------

    def predict(self, img) -> str:
        """Retourne 'pre_queue', 'in_combat', 'end_screen', ou 'unknown'."""
        model = self._load_model()
        if model is None:
            return "unknown"
        try:
            feat = _extract_features(img)
            return str(model["pipeline"].predict([feat])[0])
        except Exception as e:
            logger.error("predict: %s", e)
            return "unknown"

    def predict_outcome(self, img) -> str:
        """Retourne 'win' ou 'lose' depuis un écran de fin (règle couleur ROI haut)."""
        model = self._load_model()
        if model is None:
            return "unknown"
        rule = model.get("win_lose_rule", {})
        if not rule:
            return "unknown"
        try:
            roi = _crop_roi(img.convert("RGB"), rule["roi"])
            arr = np.asarray(roi, dtype=float)
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            brightness = (r + g + b).mean() / 3
            warm = r.mean() - b.mean()

            votes_win = 0
            if rule.get("win_is_brighter"):
                votes_win += 1 if brightness > rule["brightness_threshold"] else -1
            else:
                votes_win += 1 if brightness < rule["brightness_threshold"] else -1
            if rule.get("win_is_warmer"):
                votes_win += 1 if warm > rule["warm_threshold"] else -1
            else:
                votes_win += 1 if warm < rule["warm_threshold"] else -1

            return "win" if votes_win >= 0 else "lose"
        except Exception as e:
            logger.error("predict_outcome: %s", e)
            return "unknown"

    # ------------------------------------------------------------------
    # Interface états (utilisée par PollingLoop)
    # ------------------------------------------------------------------

    def is_pre_queue_ranked(self, img) -> bool:
        return self.predict(img) == "pre_queue"

    def is_in_combat(self, img) -> bool:
        return self.predict(img) == "in_combat"

    def is_end_screen(self, img) -> bool:
        return self.predict(img) == "end_screen"

    # ------------------------------------------------------------------
    # Calibration (conservée pour compatibilité UI — non utilisée par ML)
    # ------------------------------------------------------------------

    def calibrate(self, state_name: str, img) -> bool:
        logger.info("calibrate() ignorée — la détection utilise le modèle ML.")
        return True

    def is_calibrated(self, state_name: str) -> bool:
        return self.is_model_available()


# ---------------------------------------------------------------------------
# PollingLoop
# ---------------------------------------------------------------------------

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

    Après une transition vers END_SCREEN, polling.last_outcome vaut 'win' ou 'lose'.
    """

    def __init__(self, interval: float = 0.1, config=None, detector=None):
        self._interval = interval
        self._config = config
        self._detector = detector
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state = CombatState.IDLE
        self._mumu_detected = False
        self._last_outcome = None
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

    @property
    def last_outcome(self) -> str | None:
        """'win', 'lose' ou None — résultat du dernier combat détecté."""
        with self._lock:
            return self._last_outcome

    # ------------------------------------------------------------------
    # Configuration & cycle de vie
    # ------------------------------------------------------------------

    def set_callbacks(self, on_mumu_detected=None, on_mumu_lost=None,
                      on_state_changed=None):
        self._on_mumu_detected = on_mumu_detected
        self._on_mumu_lost = on_mumu_lost
        self._on_state_changed = on_state_changed

    def start(self):
        self._stop_event.clear()
        logger.info("PollingLoop démarrée (interval=%.3fs)", self._interval)
        self._loop()

    def stop(self):
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

        if on_detected:
            on_detected()
        if on_lost:
            on_lost()

        if self._mumu_detected and self._config is not None and self._detector is not None:
            self._detect_and_transition()

    def _detect_and_transition(self):
        region = self._config.get_all().get("mumu_region")
        if not region:
            return

        img = capture_region_pil(region)
        if img is None:
            return

        current = self.state
        try:
            next_state, outcome = self._compute_next_state(current, img)
        except Exception as e:
            logger.error("state detection error: %s", e)
            return

        if next_state != current:
            with self._lock:
                prev_state = self._state
                self._state = next_state
                if outcome is not None:
                    self._last_outcome = outcome
            logger.info("État → %s (était %s)%s", next_state.value, prev_state.value,
                        f"  outcome={outcome}" if outcome else "")
            if self._on_state_changed:
                self._on_state_changed(prev_state, next_state)

    def _compute_next_state(self, current: CombatState, img) -> tuple[CombatState, str | None]:
        """Retourne (next_state, outcome).

        outcome est 'win' ou 'lose' lors de la transition vers END_SCREEN, None sinon.
        """
        d = self._detector

        if current == CombatState.IDLE:
            if d.is_pre_queue_ranked(img):
                return CombatState.PRE_QUEUE, None

        elif current == CombatState.PRE_QUEUE:
            if d.is_in_combat(img):
                return CombatState.IN_COMBAT, None
            elif not d.is_pre_queue_ranked(img):
                return CombatState.IDLE, None

        elif current == CombatState.IN_COMBAT:
            if d.is_end_screen(img):
                outcome = d.predict_outcome(img)
                logger.info("Fin de combat détectée : %s", outcome)
                return CombatState.END_SCREEN, outcome

        elif current == CombatState.END_SCREEN:
            if not d.is_end_screen(img):
                return CombatState.IDLE, None

        return current, None
