@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  ==========================================
echo   Pokemon TCG Tracker
echo  ==========================================
echo.

:: --- Verifier que Python est installe ---
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR : Python introuvable.
    echo.
    echo  Installe Python 3.10 ou plus depuis :
    echo    https://www.python.org/downloads/
    echo.
    echo  Coche bien "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

:: --- Creer le venv si absent ---
if not exist ".venv\Scripts\python.exe" (
    echo  [1/2] Creation de l'environnement virtuel...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERREUR : creation du venv echouee.
        pause
        exit /b 1
    )
    echo  OK.
    echo.
)

:: --- Installer les dependances si pywebview absent ---
if not exist ".venv\Lib\site-packages\webview" (
    echo  [2/2] Installation des dependances...
    echo  ^(premiere fois : peut prendre 2 a 5 minutes^)
    echo.
    echo  NOTE : EasyOCR telechargera ~500 Mo de modeles
    echo  au premier lancement de la capture.
    echo.
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  ERREUR : installation echouee.
        echo  Verifie ta connexion Internet et relance.
        pause
        exit /b 1
    )
    echo.
    echo  Installation terminee.
    echo.
)

:: --- Lancer l'application ---
echo  Lancement...
echo  L'icone apparait dans la barre des taches systeme.
echo.

.venv\Scripts\python.exe main.py

:: Si l'app se ferme avec une erreur, afficher le log
if errorlevel 1 (
    echo.
    echo  L'application s'est fermee avec une erreur.
    echo  Consulte les logs : data\app.log
    echo.
    pause
)
