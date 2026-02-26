@echo off
cd /d "%~dp0"

echo.
echo  Creation du raccourci Bureau...
echo.

:: Creer le raccourci via PowerShell inline (contourne la politique d'execution)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut([System.IO.Path]::Combine($env:USERPROFILE, 'Desktop', 'Pokemon TCG Tracker.lnk')); ^
   $lnk.TargetPath = '%~dp0launch.bat'; ^
   $lnk.WorkingDirectory = '%~dp0'; ^
   $lnk.WindowStyle = 7; ^
   $lnk.Description = 'Pokemon TCG Tracker'; ^
   $lnk.Save()"

if errorlevel 1 (
    echo  ERREUR : creation du raccourci echouee.
    pause
    exit /b 1
)

echo  Raccourci "Pokemon TCG Tracker" cree sur le Bureau !
echo.
pause
