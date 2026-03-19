"""tracker/paths.py — Répertoire de données centralisé.

Utilise PTCG_DATA_DIR si défini (ex: lancement depuis un chemin réseau WSL),
sinon data/ relatif à la racine du projet.

En mode frozen (PyInstaller --onedir), data/ est adjacent à l'exe (pas dans _internal/).
"""
import os
import sys

_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)


def get_project_root() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return _PROJECT_ROOT


def get_data_dir() -> str:
    env = os.environ.get("PTCG_DATA_DIR")
    if env:
        return os.path.abspath(env)
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "data")
    return os.path.join(_PROJECT_ROOT, "data")
