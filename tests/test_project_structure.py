"""Tests de structure du projet — Story 1.1.

Valide que l'arborescence, les stubs Python, et les fichiers de config
sont correctement créés.
"""
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts):
    return os.path.join(PROJECT_ROOT, *parts)


# ---------------------------------------------------------------------------
# AC2 — Structure de dossiers
# ---------------------------------------------------------------------------

REQUIRED_DIRS = [
    "tracker",
    "tracker/capture",
    "tracker/db",
    "tracker/api",
    "ui",
    "ui/components",
    "assets",
    "build",
]

REQUIRED_INIT_FILES = [
    "tracker/__init__.py",
    "tracker/capture/__init__.py",
    "tracker/db/__init__.py",
    "tracker/api/__init__.py",
]

REQUIRED_STUB_FILES = [
    "main.py",
    "tracker/tray.py",
    "tracker/updater.py",
    "tracker/capture/screen.py",
    "tracker/capture/detector.py",
    "tracker/capture/ocr.py",
    "tracker/db/database.py",
    "tracker/db/models.py",
    "tracker/api/api.py",
]


@pytest.mark.parametrize("directory", REQUIRED_DIRS)
def test_required_directory_exists(directory):
    assert os.path.isdir(path(directory)), f"Répertoire manquant : {directory}"


@pytest.mark.parametrize("init_file", REQUIRED_INIT_FILES)
def test_python_package_init_exists(init_file):
    assert os.path.isfile(path(init_file)), f"__init__.py manquant : {init_file}"


@pytest.mark.parametrize("stub_file", REQUIRED_STUB_FILES)
def test_python_stub_exists(stub_file):
    assert os.path.isfile(path(stub_file)), f"Stub Python manquant : {stub_file}"


# ---------------------------------------------------------------------------
# AC1 — requirements.txt
# ---------------------------------------------------------------------------

REQUIRED_DEPS = [
    "pywebview==6.1",
    "easyocr==1.7.2",
    "mss==10.1.0",
    "pywin32==311",
    "pystray==0.19.5",
    "Pillow==12.1.1",
]


def test_requirements_txt_exists():
    assert os.path.isfile(path("requirements.txt"))


@pytest.mark.parametrize("dep", REQUIRED_DEPS)
def test_requirements_txt_contains_dep(dep):
    with open(path("requirements.txt")) as f:
        content = f.read()
    assert dep in content, f"Dépendance manquante dans requirements.txt : {dep}"


def test_requirements_dev_txt_exists():
    assert os.path.isfile(path("requirements-dev.txt"))


def test_requirements_dev_contains_pyinstaller():
    with open(path("requirements-dev.txt")) as f:
        content = f.read()
    assert "PyInstaller==6.19.0" in content


# ---------------------------------------------------------------------------
# AC3 — .gitignore
# ---------------------------------------------------------------------------

def test_gitignore_exists():
    assert os.path.isfile(path(".gitignore"))


def test_gitignore_excludes_data():
    with open(path(".gitignore")) as f:
        content = f.read()
    assert "data/" in content, ".gitignore doit exclure data/"


def test_gitignore_excludes_venv():
    with open(path(".gitignore")) as f:
        content = f.read()
    assert ".venv/" in content


# ---------------------------------------------------------------------------
# TrackerAPI stub (requis par Story 1.3 — MC-01)
# ---------------------------------------------------------------------------

def test_tracker_api_stub_has_class():
    """tracker/api/api.py doit définir une classe TrackerAPI (même vide)."""
    with open(path("tracker/api/api.py")) as f:
        content = f.read()
    assert "class TrackerAPI" in content, "TrackerAPI class manquante dans api.py"
