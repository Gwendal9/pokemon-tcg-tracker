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
    echo  [1/3] Creation de l'environnement virtuel...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERREUR : creation du venv echouee.
        pause
        exit /b 1
    )
    echo  OK.
    echo.
)

:: --- Installer les dependances Python si pywebview absent ---
if not exist ".venv\Lib\site-packages\webview" (
    echo  [2/3] Installation des dependances Python...
    echo  ^(premiere fois : peut prendre 2 a 5 minutes^)
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

:: --- Telecharger les dependances JS si absentes ---
if not exist "ui\vendor\chart.min.js" (
    echo  [3/3] Telechargement des dependances UI...
    if not exist "ui\vendor" mkdir "ui\vendor"
    curl -sL "https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" -o "ui\vendor\daisyui.min.css"
    curl -sL "https://cdn.tailwindcss.com" -o "ui\vendor\tailwind.min.js"
    curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js" -o "ui\vendor\chart.min.js"
    echo  OK.
    echo.
)

:: --- Lancer l'application ---
echo  Lancement...
echo  L'icone apparait dans la barre des taches systeme ^(fleche ^ en bas a droite^).
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
