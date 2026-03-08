"""tools/train_classifier.py — Entraîne le classificateur d'état de jeu.

Architecture à deux étapes :
  1. SVM 3 classes : pre_queue / in_combat / end_screen
  2. Règle couleur   : end_screen → win ou lose (fond chaud = victoire, froid = défaite)

Usage :
    python tools/train_classifier.py

Sortie : data/state_classifier.pkl
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pickle
import random

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Labels sources sur disque
SRC_LABELS = ["pre_queue", "in_combat", "end_screen_win", "end_screen_lose"]
# Labels du classificateur stage 1
CLS_LABELS = ["pre_queue", "in_combat", "end_screen"]

IMG_SIZE = (160, 120)
# Bande du haut : fond bleu/pastel (victoire) vs orange/saumon (défaite)
WIN_LOSE_ROI = (0.0, 0.0, 1.0, 0.10)


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def extract_features(img: Image.Image) -> np.ndarray:
    from skimage.feature import hog  # noqa: PLC0415

    img_rgb = img.convert("RGB").resize(IMG_SIZE, Image.LANCZOS)
    arr = np.asarray(img_rgb, dtype=np.uint8)

    gray = np.asarray(img_rgb.convert("L"), dtype=np.uint8)
    hog_feat = hog(
        gray,
        orientations=8,
        pixels_per_cell=(16, 16),
        cells_per_block=(2, 2),
        feature_vector=True,
    )

    hsv_arr = _rgb_to_hsv(arr)
    hist_feats = []
    for ch in range(3):
        hist, _ = np.histogram(hsv_arr[:, :, ch], bins=16, range=(0, 1))
        hist_feats.append(hist / (hist.sum() + 1e-6))

    return np.concatenate([hog_feat, np.concatenate(hist_feats)])


def _rgb_to_hsv(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[:,:,0]/255., arr[:,:,1]/255., arr[:,:,2]/255.
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    h = np.zeros_like(r)
    s = np.where(cmax > 0, delta / cmax, 0.)
    v = cmax
    mr, mg, mb = (delta > 0) & (cmax == r), (delta > 0) & (cmax == g), (delta > 0) & (cmax == b)
    h[mr] = ((g[mr] - b[mr]) / delta[mr]) % 6
    h[mg] = (b[mg] - r[mg]) / delta[mg] + 2
    h[mb] = (r[mb] - g[mb]) / delta[mb] + 4
    h /= 6.
    return np.stack([h, s, v], axis=2)


# ---------------------------------------------------------------------------
# Règle win/lose sur couleur du fond
# ---------------------------------------------------------------------------

def calibrate_win_lose_rule(samples_dir: str) -> dict:
    """Calcule les stats de couleur sur la ROI centrale pour win et lose."""
    stats = {}
    for outcome in ("end_screen_win", "end_screen_lose"):
        folder = os.path.join(samples_dir, outcome)
        if not os.path.isdir(folder):
            continue
        files = [f for f in os.listdir(folder) if f.lower().endswith(".png")]
        brightnesses = []
        warm_scores = []
        for fname in files:
            try:
                img = Image.open(os.path.join(folder, fname)).convert("RGB")
                roi = _crop_roi(img, WIN_LOSE_ROI)
                arr = np.asarray(roi, dtype=float)
                r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
                brightnesses.append((r + g + b).mean() / 3)
                # Score "chaleur" : rouge - bleu (+ = orange/défaite, - = bleu/victoire)
                warm_scores.append(r.mean() - b.mean())
            except Exception:
                pass
        if brightnesses:
            stats[outcome] = {
                "brightness_mean": float(np.mean(brightnesses)),
                "brightness_std":  float(np.std(brightnesses)),
                "warm_mean":       float(np.mean(warm_scores)),
                "warm_std":        float(np.std(warm_scores)),
                "n":               len(brightnesses),
            }
            logger.info(
                "%s : brightness=%.1f±%.1f  warm=%.1f±%.1f  (n=%d)",
                outcome,
                stats[outcome]["brightness_mean"], stats[outcome]["brightness_std"],
                stats[outcome]["warm_mean"],        stats[outcome]["warm_std"],
                stats[outcome]["n"],
            )

    # Calcule le seuil optimal entre win et lose
    rule = {"roi": WIN_LOSE_ROI}
    if "end_screen_win" in stats and "end_screen_lose" in stats:
        w = stats["end_screen_win"]
        l = stats["end_screen_lose"]
        rule["brightness_threshold"] = (w["brightness_mean"] + l["brightness_mean"]) / 2
        rule["warm_threshold"]       = (w["warm_mean"]       + l["warm_mean"])       / 2
        # On détermine quel côté est win (lumineux ou chaud ?)
        rule["win_is_brighter"] = w["brightness_mean"] > l["brightness_mean"]
        rule["win_is_warmer"]   = w["warm_mean"]       > l["warm_mean"]
        logger.info(
            "Règle win/lose : seuil brightness=%.1f  seuil warm=%.1f  "
            "(win_brighter=%s  win_warmer=%s)",
            rule["brightness_threshold"], rule["warm_threshold"],
            rule["win_is_brighter"], rule["win_is_warmer"],
        )
    else:
        logger.warning("Pas assez de données pour calibrer la règle win/lose.")

    return rule


def _crop_roi(img: Image.Image, roi: tuple) -> Image.Image:
    w, h = img.size
    x0 = int(roi[0] * w)
    y0 = int(roi[1] * h)
    x1 = int((roi[0] + roi[2]) * w)
    y1 = int((roi[1] + roi[3]) * h)
    return img.crop((x0, y0, x1, y1))


def predict_win_lose(img: Image.Image, rule: dict) -> str:
    """Prédit 'end_screen_win' ou 'end_screen_lose' via règle couleur."""
    roi = _crop_roi(img.convert("RGB"), rule["roi"])
    arr = np.asarray(roi, dtype=float)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    brightness = (r + g + b).mean() / 3
    warm = r.mean() - b.mean()

    # Vote entre les deux indicateurs
    votes_win = 0
    if rule.get("win_is_brighter"):
        votes_win += 1 if brightness > rule["brightness_threshold"] else -1
    else:
        votes_win += 1 if brightness < rule["brightness_threshold"] else -1
    if rule.get("win_is_warmer"):
        votes_win += 1 if warm > rule["warm_threshold"] else -1
    else:
        votes_win += 1 if warm < rule["warm_threshold"] else -1

    return "end_screen_win" if votes_win >= 0 else "end_screen_lose"


# ---------------------------------------------------------------------------
# Dataset stage 1
# ---------------------------------------------------------------------------

def load_dataset(samples_dir: str):
    X, y = [], []
    counts = {}

    label_map = {
        "pre_queue":      "pre_queue",
        "in_combat":      "in_combat",
        "end_screen_win": "end_screen",
        "end_screen_lose":"end_screen",
    }

    for src_label in SRC_LABELS:
        folder = os.path.join(samples_dir, src_label)
        cls_label = label_map[src_label]
        if not os.path.isdir(folder):
            counts[src_label] = 0
            continue
        files = [f for f in os.listdir(folder) if f.lower().endswith(".png")]
        counts[src_label] = len(files)
        for fname in files:
            try:
                img = Image.open(os.path.join(folder, fname))
                X.append(extract_features(img))
                y.append(cls_label)
            except Exception as e:
                logger.warning("Erreur %s : %s", fname, e)

    logger.info("Images chargées : %s", counts)
    logger.info("Classes stage 1 : %s", {l: y.count(l) for l in set(y)})
    return np.array(X), np.array(y), counts


# ---------------------------------------------------------------------------
# Entraînement
# ---------------------------------------------------------------------------

def train(X, y):
    from sklearn.model_selection import StratifiedKFold, cross_val_score  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415
    from sklearn.svm import SVC  # noqa: PLC0415

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm", SVC(kernel="rbf", C=10, gamma="scale",
                    probability=True, class_weight="balanced")),
    ])

    classes, class_counts = np.unique(y, return_counts=True)
    n_splits = min(5, int(class_counts.min()))
    n_splits = max(2, n_splits)

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    logger.info("CV accuracy (%d folds) : %.1f%% ± %.1f%%",
                n_splits, scores.mean() * 100, scores.std() * 100)

    pipeline.fit(X, y)
    return pipeline


def print_report(pipeline, X, y):
    from sklearn.metrics import classification_report, confusion_matrix  # noqa: PLC0415

    present = sorted(set(y))
    y_pred = pipeline.predict(X)
    print("\n--- Rapport stage 1 ---")
    print(classification_report(y, y_pred, labels=present, zero_division=0))
    print("Matrice de confusion :")
    cm = confusion_matrix(y, y_pred, labels=present)
    col_w = 14
    print(" " * col_w + "".join(l[:col_w].ljust(col_w) for l in present))
    for i, label in enumerate(present):
        print(label[:col_w].ljust(col_w) + "".join(str(v).ljust(col_w) for v in cm[i]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    from tracker.paths import get_data_dir  # noqa: PLC0415

    data_dir    = get_data_dir()
    samples_dir = os.path.join(data_dir, "detection_samples")
    model_path  = os.path.join(data_dir, "state_classifier.pkl")

    logger.info("Dossier samples : %s", samples_dir)

    # Stage 1 : classificateur 3 classes
    X, y, counts_raw = load_dataset(samples_dir)

    if len(X) == 0:
        logger.error("Aucune image trouvée dans %s", samples_dir)
        sys.exit(1)

    present_classes = set(y)
    if len(present_classes) < 2:
        logger.error("Il faut au moins 2 classes.")
        sys.exit(1)

    pipeline = train(X, y)
    print_report(pipeline, X, y)

    # Stage 2 : calibration règle win/lose
    win_lose_rule = calibrate_win_lose_rule(samples_dir)

    # Sauvegarde
    model = {
        "pipeline":      pipeline,
        "cls_labels":    CLS_LABELS,
        "win_lose_rule": win_lose_rule,
        "img_size":      IMG_SIZE,
    }
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("Modèle sauvegardé : %s", model_path)
    print(f"\nModèle : {model_path}")


if __name__ == "__main__":
    main()
