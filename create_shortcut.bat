@echo off
cd /d "%~dp0"

echo.
echo  Creation du raccourci Bureau...
echo.

:: Ecrire le script PowerShell dans un fichier temporaire
set "TMP_PS=%TEMP%\ptcg_shortcut.ps1"

echo $shell = New-Object -ComObject WScript.Shell > "%TMP_PS%"
echo $lnk = $shell.CreateShortcut([System.IO.Path]::Combine($env:USERPROFILE, 'Desktop', 'Pokemon TCG Tracker.lnk')) >> "%TMP_PS%"
echo $lnk.TargetPath = '%~dp0launch.bat' >> "%TMP_PS%"
echo $lnk.WorkingDirectory = '%~dp0' >> "%TMP_PS%"
echo $lnk.WindowStyle = 7 >> "%TMP_PS%"
echo $lnk.Description = 'Pokemon TCG Tracker' >> "%TMP_PS%"
echo $lnk.Save() >> "%TMP_PS%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TMP_PS%"

if errorlevel 1 (
    echo  ERREUR : creation du raccourci echouee.
    del "%TMP_PS%" 2>nul
    pause
    exit /b 1
)

del "%TMP_PS%" 2>nul
echo  Raccourci "Pokemon TCG Tracker" cree sur le Bureau !
echo.
pause
