@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

echo.
echo  ==========================================
echo   Pokemon TCG Tracker
echo  ==========================================
echo.

:: --- Chemins locaux Windows (pas reseau/WSL) ---
set VENV_DIR=%LOCALAPPDATA%\pokemon-tcg-tracker\.venv
set PTCG_DATA_DIR=%LOCALAPPDATA%\pokemon-tcg-tracker\data

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
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo  [1/3] Creation de l'environnement virtuel...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  ERREUR : creation du venv echouee.
        pause
        exit /b 1
    )
    echo  OK.
    echo.
)

:: --- Installer les dependances Python si pywebview absent ---
if not exist "%VENV_DIR%\Lib\site-packages\webview" (
    echo  [2/3] Installation des dependances Python...
    echo  ^(premiere fois : peut prendre 2 a 5 minutes^)
    echo.
    "%VENV_DIR%\Scripts\pip" install -r requirements.txt
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
    echo  [3/4] Telechargement des dependances UI...
    if not exist "ui\vendor" mkdir "ui\vendor"
    curl -sL "https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" -o "ui\vendor\daisyui.min.css"
    curl -sL "https://cdn.tailwindcss.com" -o "ui\vendor\tailwind.min.js"
    curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js" -o "ui\vendor\chart.min.js"
    echo  OK.
    echo.
)

:: --- Telecharger les icones energies et rangs si absents ---
if not exist "ui\vendor\energy\fire.png" (
    echo  [4/4] Telechargement des icones energies et rangs...
    if not exist "ui\vendor\energy" mkdir "ui\vendor\energy"
    if not exist "ui\vendor\ranks"  mkdir "ui\vendor\ranks"

    set BASE_ENERGY=https://archives.bulbagarden.net/media/upload
    curl -sL "%BASE_ENERGY%/a/ad/Fire-attack.png"       -o "ui\vendor\energy\fire.png"
    curl -sL "%BASE_ENERGY%/1/11/Water-attack.png"      -o "ui\vendor\energy\water.png"
    curl -sL "%BASE_ENERGY%/2/2e/Grass-attack.png"      -o "ui\vendor\energy\grass.png"
    curl -sL "%BASE_ENERGY%/0/04/Lightning-attack.png"  -o "ui\vendor\energy\lightning.png"
    curl -sL "%BASE_ENERGY%/e/ef/Psychic-attack.png"    -o "ui\vendor\energy\psychic.png"
    curl -sL "%BASE_ENERGY%/4/48/Fighting-attack.png"   -o "ui\vendor\energy\fighting.png"
    curl -sL "%BASE_ENERGY%/a/ab/Darkness-attack.png"   -o "ui\vendor\energy\darkness.png"
    curl -sL "%BASE_ENERGY%/6/64/Metal-attack.png"      -o "ui\vendor\energy\metal.png"
    curl -sL "%BASE_ENERGY%/1/1d/Colorless-attack.png"  -o "ui\vendor\energy\colorless.png"
    curl -sL "%BASE_ENERGY%/8/8a/Dragon-attack.png"     -o "ui\vendor\energy\dragon.png"

    set BASE_RANKS=https://archives.bulbagarden.net/media/upload
    curl -sL "%BASE_RANKS%/6/65/TCGP_Icon_Beginner_Rank.png"                  -o "ui\vendor\ranks\beginner.png"
    curl -sL "%BASE_RANKS%/1/11/TCGP_Icon_Pok%%C3%%A9_Ball_Rank.png"          -o "ui\vendor\ranks\pokeball.png"
    curl -sL "%BASE_RANKS%/2/27/TCGP_Icon_Great_Ball_Rank.png"                -o "ui\vendor\ranks\greatball.png"
    curl -sL "%BASE_RANKS%/f/f3/TCGP_Icon_Ultra_Ball_Rank.png"                -o "ui\vendor\ranks\ultraball.png"
    curl -sL "%BASE_RANKS%/7/7e/TCGP_Icon_Master_Ball_Rank.png"               -o "ui\vendor\ranks\masterball.png"

    echo  OK.
    echo.
)

:: --- Lancer l'application ---
echo  Lancement...
echo  L'icone apparait dans la barre des taches systeme ^(fleche ^ en bas a droite^).
echo.

"%VENV_DIR%\Scripts\python.exe" main.py

:: Si l'app se ferme avec une erreur, afficher le log
if errorlevel 1 (
    echo.
    echo  L'application s'est fermee avec une erreur.
    echo  Consulte les logs : data\app.log
    echo.
    pause
)
