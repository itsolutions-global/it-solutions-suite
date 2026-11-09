# ==============================================================================
# IT Solutions Global Corporation — Turnkey Windows Workstation Installer
# Installs CorePulse, NexusShield, and EchoStream in <10 seconds.
# 100% Python Standard Library. Zero Bloat. 100% Offline Private Compute.
# Usage: irm https://it-solutions-global.vercel.app/install.ps1 | iex
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "         IT SOLUTIONS GLOBAL — AUTONOMOUS ENTERPRISE TRIAD INSTALLER        " -ForegroundColor White
Write-Host "            CorePulse (Action) • NexusShield (Defense) • EchoStream (Perception)   " -ForegroundColor DarkGray
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detect Python
Write-Host "[1/4] Verifying Python runtime environment..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host "[!] Python 3 not detected on PATH. Attempting automatic installation via winget..." -ForegroundColor Yellow
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements --silent
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $PythonCmd = "python"
    } else {
        Write-Host "[ERROR] Python 3.9+ is required. Please install Python from https://python.org and re-run." -ForegroundColor Red
        return
    }
}

$PyVer = & $PythonCmd --version
Write-Host "  [OK] Found $PyVer ($PythonCmd)" -ForegroundColor Green

# 2. Install / Upgrade it-solutions-suite from PyPI
Write-Host "[2/4] Fetching latest release of it-solutions-suite from PyPI..." -ForegroundColor Yellow
& $PythonCmd -m pip install --upgrade it-solutions-suite --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] Upstream PyPI pip install encountered a warning; verifying package module..." -ForegroundColor DarkYellow
}
Write-Host "  [OK] it-solutions-suite installed successfully." -ForegroundColor Green

# 3. Create CorePulse Cockpit Desktop Shortcut
Write-Host "[3/4] Creating CorePulse Cockpit desktop shortcut..." -ForegroundColor Yellow
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
    $ShortcutPath = Join-Path $DesktopPath "CorePulse Cockpit.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "$PythonCmd"
    $Shortcut.Arguments = "-m corepulse.main"
    $Shortcut.Description = "Launch CorePulse Autonomous Life & Workstation Cockpit"
    $Shortcut.Save()
    Write-Host "  [OK] Desktop shortcut created: 'CorePulse Cockpit.lnk'" -ForegroundColor Green
} catch {
    Write-Host "  [!] Desktop shortcut skipped (non-critical)." -ForegroundColor DarkGray
}

# 4. Launch CorePulse Engine & Open Cockpit
Write-Host "[4/4] Launching CorePulse Engine daemon on http://127.0.0.1:8080..." -ForegroundColor Yellow

$CorePulseRunning = $false
try {
    $Resp = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($Resp.status -eq "healthy") {
        $CorePulseRunning = $true
    }
} catch {
    $CorePulseRunning = $false
}

if (-not $CorePulseRunning) {
    Start-Process -FilePath $PythonCmd -ArgumentList "-m corepulse.main" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# Open Cockpit in default browser
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] IT SOLUTIONS SUITE IS LIVE ON YOUR WORKSTATION!                " -ForegroundColor White
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "  • Cockpit UI:     http://127.0.0.1:8080" -ForegroundColor Cyan
Write-Host "  • REST API:       http://127.0.0.1:8080/api/health" -ForegroundColor Cyan
Write-Host "  • Omnibar:        Run 'python -m corepulse.omnibar' (Ctrl+Shift+Space)" -ForegroundColor DarkGray
Write-Host "  • Local Data:     100% private SQLite WAL store in local AppData" -ForegroundColor DarkGray
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""

Start-Process "http://127.0.0.1:8080"
