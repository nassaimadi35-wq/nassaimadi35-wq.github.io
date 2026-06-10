# Installateur automatique — Contrôle PC à distance (Windows)
# Usage (PowerShell) :
#   irm https://raw.githubusercontent.com/nassaimadi35-wq/nassaimadi35-wq.github.io/claude/remote-pc-control-app-rgbmo9/remote-pc/installer.ps1 | iex

$ErrorActionPreference = "Stop"
$repo   = "nassaimadi35-wq/nassaimadi35-wq.github.io"
$branch = "claude/remote-pc-control-app-rgbmo9"
$dest   = Join-Path $HOME "RemotePC"

Write-Host ""
Write-Host "=== Installation du Contrôle PC à distance ===" -ForegroundColor Cyan

# --- 1. Python ---
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    # Sur Windows, "python" peut être l'alias du Microsoft Store qui ne fait rien
    $ver = & python --version 2>&1
    if ($ver -notmatch "Python 3") { $python = $null }
}
if (-not $python) {
    Write-Host "[1/4] Python introuvable, installation via winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Python installé : fermez puis rouvrez PowerShell et relancez la commande." -ForegroundColor Yellow
        exit
    }
} else {
    Write-Host "[1/4] Python déjà présent : $(& python --version)" -ForegroundColor Green
}

# --- 2. Téléchargement de l'application ---
Write-Host "[2/4] Téléchargement de l'application..."
$zip = Join-Path $env:TEMP "remote-pc.zip"
$tmp = Join-Path $env:TEMP "remote-pc-extract"
Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/$branch.zip" -OutFile $zip
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive $zip -DestinationPath $tmp
$src = Get-ChildItem $tmp -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $src.FullName "remote-pc\*") $dest -Recurse -Force
Remove-Item $zip, $tmp -Recurse -Force
Write-Host "      Installé dans $dest" -ForegroundColor Green

# --- 3. Dépendances ---
Write-Host "[3/4] Installation des dépendances Python..."
& python -m pip install --quiet --upgrade pip
& python -m pip install --quiet -r (Join-Path $dest "requirements.txt")

# --- 4. Raccourci sur le Bureau ---
Write-Host "[4/4] Création du raccourci sur le Bureau..."
$desktop = [Environment]::GetFolderPath("Desktop")
$batPath = Join-Path $desktop "Contrôle PC à distance.bat"
"@echo off`r`ncd /d `"$dest`"`r`npython server.py`r`npause" | Set-Content -Path $batPath -Encoding ASCII

Write-Host ""
Write-Host "=== Installation terminée ! ===" -ForegroundColor Green
Write-Host "Un raccourci 'Contrôle PC à distance' a été créé sur votre Bureau."
Write-Host "Si Windows demande l'autorisation pare-feu au premier lancement, cliquez 'Autoriser'."
Write-Host ""
Write-Host "Démarrage du serveur..." -ForegroundColor Cyan
Set-Location $dest
& python server.py
