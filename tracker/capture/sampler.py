"""tracker/capture/sampler.py — Détection de changements visuels + capture automatique.

SamplingLoop : tourne en thread daemon, compare les frames successifs,
sauvegarde dans data/detection_samples/unlabeled/ quand un gros changement
est détecté. Inclut une heuristique de pré-labélisation basée sur les couleurs.

Labels possibles : pre_queue, in_combat, end_screen_win, end_screen_lose, unknown
"""
import logging
import os
import threading
import time
from datetime import datetime

from PIL import Image

from tracker.paths import get_data_dir

logger = logging.getLogger(__name__)

_SAMPLES_DIR = os.path.join(get_data_dir(), "detection_samples")
_UNLABELED_DIR = os.path.join(_SAMPLES_DIR, "unlabeled")

# Seuil MSE au-dessus duquel on considère qu'il y a un changement significatif
_CHANGE_THRESHOLD = 1500.0

# Intervalle entre deux captures (secondes)
_POLL_INTERVAL = 0.8

# Éviter de sauvegarder plusieurs fois le même changement (cooldown en secondes)
_SAVE_COOLDOWN = 2.0


# ---------------------------------------------------------------------------
# Heuristiques de pré-labélisation
# ---------------------------------------------------------------------------

def _dominant_colors(img, region_frac):
    """Retourne la couleur moyenne (R,G,B) dans une zone fractionnaire de l'image."""
    import numpy as np  # noqa: PLC0415
    w, h = img.size
    x0 = int(region_frac[0] * w)
    y0 = int(region_frac[1] * h)
    x1 = int((region_frac[0] + region_frac[2]) * w)
    y1 = int((region_frac[1] + region_frac[3]) * h)
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    arr = __import__("numpy").asarray(crop, dtype=float)
    return arr.mean(axis=(0, 1))  # [R, G, B]


def guess_label(img) -> str:
    """Tente de deviner le label d'une image via heuristiques couleur.

    Heuristiques basées sur les observations de Pokemon TCG Pocket :
    - end_screen_win  : bandeau central très lumineux (or/jaune/blanc)
    - end_screen_lose : bandeau central sombre (violet/bleu foncé)
    - in_combat       : bandes haut/bas avec UI de jeu (couleurs mixtes modérées)
    - pre_queue       : fond spécifique file d'attente
    - unknown         : si aucune heuristique ne matche
    """
    try:
        import numpy as np  # noqa: PLC0415

        # Zone centrale haute — là où apparaît le bandeau victoire/défaite
        center = _dominant_colors(img, (0.15, 0.30, 0.70, 0.25))
        r, g, b = center

        brightness = (r + g + b) / 3

        # Bandeau très lumineux → probablement victoire
        if brightness > 180 and r > 150 and g > 130:
            return "end_screen_win"

        # Bandeau sombre avec dominante bleue/violette → probablement défaite
        if brightness < 100 and b > r and b > g:
            return "end_screen_lose"

        # Zone bas-gauche (score joueur) — présente en combat
        bottom_left = _dominant_colors(img, (0.00, 0.85, 0.40, 0.12))
        bl_brightness = bottom_left.mean()

        # Zone haut-droite (score adversaire)
        top_right = _dominant_colors(img, (0.58, 0.00, 0.42, 0.12))
        tr_brightness = top_right.mean()

        # Si les deux zones UI de combat ont du contenu (pas trop sombres)
        if bl_brightness > 60 and tr_brightness > 60:
            return "in_combat"

        return "unknown"

    except Exception as e:
        logger.debug("guess_label erreur: %s", e)
        return "unknown"


# ---------------------------------------------------------------------------
# SamplingLoop
# ---------------------------------------------------------------------------

class SamplingLoop:
    """Capture automatiquement des frames quand un gros changement visuel est détecté.

    Usage :
        sampler = SamplingLoop(config=config_manager)
        thread = threading.Thread(target=sampler.start, daemon=True)
        thread.start()
        ...
        sampler.stop()
    """

    def __init__(self, config=None, interval: float = _POLL_INTERVAL):
        self._config = config
        self._interval = interval
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._running = False
        self._prev_frame = None
        self._last_save_time = 0.0
        self._saved_count = 0

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def start(self):
        with self._lock:
            self._running = True
            self._prev_frame = None
            self._saved_count = 0
        self._stop_event.clear()
        os.makedirs(_UNLABELED_DIR, exist_ok=True)
        logger.info("SamplingLoop démarrée (interval=%.1fs, seuil MSE=%.0f)",
                    self._interval, _CHANGE_THRESHOLD)
        self._loop()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._running = False
        logger.info("SamplingLoop arrêtée (%d captures sauvegardées)", self._saved_count)

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def saved_count(self) -> int:
        with self._lock:
            return self._saved_count

    # ------------------------------------------------------------------
    # Boucle interne
    # ------------------------------------------------------------------

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error("SamplingLoop tick error: %s", e)
            self._stop_event.wait(self._interval)

    def _tick(self):
        from tracker.capture.screen import capture_region_pil  # noqa: PLC0415

        if self._config is None:
            return
        region = self._config.get_all().get("mumu_region")
        if not region:
            return

        img = capture_region_pil(region)
        if img is None:
            return

        with self._lock:
            prev = self._prev_frame
            self._prev_frame = img

        if prev is None:
            return

        mse = self._mse(img, prev)
        if mse < _CHANGE_THRESHOLD:
            return

        now = time.monotonic()
        if now - self._last_save_time < _SAVE_COOLDOWN:
            return

        self._last_save_time = now
        self._save(img, mse)

    def _mse(self, img_a, img_b) -> float:
        try:
            import numpy as np  # noqa: PLC0415
            a = __import__("numpy").asarray(
                img_a.convert("RGB").resize((320, 240), Image.LANCZOS), dtype=float)
            b = __import__("numpy").asarray(
                img_b.convert("RGB").resize((320, 240), Image.LANCZOS), dtype=float)
            return float(__import__("numpy").mean((a - b) ** 2))
        except Exception:
            return 0.0

    def _save(self, img, mse: float):
        label = guess_label(img)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{ts}_{label}.png"
        path = os.path.join(_UNLABELED_DIR, filename)
        try:
            img.convert("RGB").save(path)
            with self._lock:
                self._saved_count += 1
            logger.info("Capture sauvegardée: %s  (MSE=%.0f label=%s)", filename, mse, label)
        except Exception as e:
            logger.error("SamplingLoop _save: %s", e)


# ---------------------------------------------------------------------------
# Helpers pour l'API
# ---------------------------------------------------------------------------

def list_unlabeled() -> list[dict]:
    """Retourne la liste des fichiers non labélisés avec leur label auto-détecté."""
    if not os.path.isdir(_UNLABELED_DIR):
        return []
    result = []
    for fname in sorted(os.listdir(_UNLABELED_DIR)):
        if not fname.lower().endswith(".png"):
            continue
        parts = fname.rsplit("_", 1)
        auto_label = parts[1].replace(".png", "") if len(parts) == 2 else "unknown"
        result.append({
            "filename": fname,
            "path": os.path.join(_UNLABELED_DIR, fname),
            "auto_label": auto_label,
        })
    return result


def label_sample(filename: str, label: str) -> bool:
    """Déplace filename de unlabeled/ vers detection_samples/{label}/.

    Args:
        filename: nom du fichier PNG dans unlabeled/.
        label: 'pre_queue', 'in_combat', 'end_screen_win', 'end_screen_lose' ou 'delete'.

    Returns:
        True si succès.
    """
    valid_labels = {"pre_queue", "in_combat", "end_screen_win", "end_screen_lose"}
    src = os.path.join(_UNLABELED_DIR, filename)
    if not os.path.isfile(src):
        logger.warning("label_sample: fichier introuvable %s", filename)
        return False

    if label == "delete":
        os.remove(src)
        return True

    if label not in valid_labels:
        logger.warning("label_sample: label invalide %r", label)
        return False

    dest_dir = os.path.join(_SAMPLES_DIR, label)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, filename)
    os.replace(src, dest)
    logger.info("label_sample: %s → %s/", filename, label)
    return True
