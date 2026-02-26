# create_shortcut.ps1 — Cree un raccourci bureau pour Pokemon TCG Tracker
# Lancer : clic droit > "Executer avec PowerShell"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LaunchBat  = Join-Path $ProjectDir "launch.bat"
$Desktop    = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
$Shortcut   = Join-Path $Desktop "Pokemon TCG Tracker.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Lnk = $WshShell.CreateShortcut($Shortcut)
$Lnk.TargetPath       = $LaunchBat
$Lnk.WorkingDirectory = $ProjectDir
$Lnk.WindowStyle      = 7        # 7 = fenetre minimisee (console flash rapide)
$Lnk.Description      = "Pokemon TCG Tracker"
$Lnk.Save()

Write-Host ""
Write-Host "  Raccourci cree sur le Bureau :" -ForegroundColor Green
Write-Host "  $Shortcut" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Double-clique dessus pour lancer l'application." -ForegroundColor White
Write-Host ""
Read-Host "  Appuie sur Entree pour fermer"
