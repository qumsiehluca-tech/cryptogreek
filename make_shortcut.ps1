# make_shortcut.ps1
# Creates a desktop shortcut "Cryptogreek" with the gold-phi icon,
# launching the app via pyw.exe (no console window).

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath    = Join-Path $projectDir "app.py"
$iconPath   = Join-Path $projectDir "icon.ico"

if (-not (Test-Path $appPath)) {
    Write-Error "Cannot find app.py next to this script."
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not (Test-Path $iconPath)) {
    Write-Warning "icon.ico not found - run 'py make_icon.py' first if you want the custom icon."
    $iconPath = $null
}

$launcher = (Get-Command pyw.exe -ErrorAction SilentlyContinue).Source
if (-not $launcher) {
    $launcher = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
}
if (-not $launcher) {
    $launcher = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}
if (-not $launcher) {
    Write-Error "Couldn't find pyw.exe, py.exe, or python.exe on PATH."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using launcher: $launcher"

$desktop      = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Cryptogreek.lnk"

$shell    = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = $launcher
$shortcut.Arguments        = "`"$appPath`""
$shortcut.WorkingDirectory = $projectDir
if ($iconPath) { $shortcut.IconLocation = "$iconPath,0" }
$shortcut.Description      = "Cryptogreek - translate English to French, render in Greek letters"
$shortcut.WindowStyle      = 7
$shortcut.Save()

Write-Host ""
Write-Host "Created shortcut: $shortcutPath" -ForegroundColor Green
Write-Host "Double-click the gold-phi seal on your desktop to launch." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
