"""tracker/paths.py — Répertoire de données centralisé.

Utilise PTCG_DATA_DIR si défini (ex: lancement depuis un chemin réseau WSL),
sinon data/ relatif à la racine du projet.
"""
import os

_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)


def get_data_dir() -> str:
    env = os.environ.get("PTCG_DATA_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.join(_PROJECT_ROOT, "data")
