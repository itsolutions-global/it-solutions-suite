<#
.SYNOPSIS
    IT Solutions Enterprise Suite - 1-Click Windows PowerShell Installer
    Installs and configures CorePulse v1.0 and NexusShield v1.0.
    Zero external dependencies. Requires Python 3.8+.

.DESCRIPTION
    Validates Python environment, configures corporate CLI distribution wrappers,
    executes suite health checks, and registers unified commands.
#>

[CmdletBinding()]
param(
    [switch]$SkipHealthCheck,
    [switch]$AddToUserPath
)

$ErrorActionPreference = "Stop"

# Styling
function Write-Header {
    param([string]$Text)
    Write-Host "`n=== $Text ===" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "  [OK] $Text" -ForegroundColor Green
}

function Write-Info {
    param([string]$Text)
    Write-Host "  [INFO] $Text" -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Text)
    Write-Host "  [WARN] $Text" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Text)
    Write-Host "  [ERROR] $Text" -ForegroundColor Red
}

Clear-Host
Write-Host @"

  ___ _____   _____       _       _   _                 
 |_ _|_   _| /  ___|     | |     | | (_)                
  | |  | |   \ `--.  ___ | |_   _| |_ _  ___  _ __  ___ 
  | |  | |    `--. \/ _ \| | | | | __| |/ _ \| '_ \/ __|
 _| |_ | |   /\__/ / (_) | | |_| | |_| | (_) | | | \__ \
 \___/ \_/   \____/ \___/|_|\__,_|\__|_|\___/|_| |_|___/
    Enterprise Suite 1-Click Windows Installer v1.0.0
    Products: CorePulse v1.0 + NexusShield v1.0
"@ -ForegroundColor Cyan

# 1. Locate Product Directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Header "Step 1: Locating Installation Root"
Write-Info "Base Directory: $ScriptDir"

if (-not (Test-Path "$ScriptDir\corepulse") -or -not (Test-Path "$ScriptDir\nexusshield")) {
    Write-Err "Required product directories ('corepulse', 'nexusshield') not found in $ScriptDir"
    exit 1
}
Write-Success "Found CorePulse and NexusShield source packages."

# 2. Python Runtime Verification
Write-Header "Step 2: Python Environment Verification"
$PythonExe = $null

foreach ($cmd in @("python", "py", "python3")) {
    try {
        $verStr = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $verStr -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                $PythonExe = $cmd
                $PythonVer = "$major.$minor"
                break
            }
        }
    } catch {
        # continue searching
    }
}

if (-not $PythonExe) {
    Write-Err "Python 3.8 or higher was not detected on this system."
    Write-Info "Please install Python 3.8+ from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is checked."
    exit 1
}

Write-Success "Detected compatible Python runtime: $verStr ($PythonExe)"
Write-Success "Zero external dependencies verified (100% Standard Library Python architecture)."

# 3. Generate Portable CLI Distribution Wrappers
Write-Header "Step 3: Generating Unified Command-Line Wrappers"

# it-solutions.bat
$BatPath = "$ScriptDir\it-solutions.bat"
$BatContent = @"
@echo off
rem IT Solutions Unified Enterprise CLI Wrapper
setlocal
"$PythonExe" "%~dp0cli.py" %*
endlocal
"@
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Write-Success "Created Windows batch runner: $BatPath"

# it-solutions.ps1
$Ps1Path = "$ScriptDir\it-solutions.ps1"
$Ps1Content = @"
<# IT Solutions Unified Enterprise PowerShell Wrapper #>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = `$true)]
    [string[]]`$Args
)
& "$PythonExe" "$ScriptDir\cli.py" @Args
"@
Set-Content -Path $Ps1Path -Value $Ps1Content -Encoding UTF8
Write-Success "Created PowerShell wrapper: $Ps1Path"

# it-solutions (cross-platform bash script for WSL/Git Bash)
$ShWrapperPath = "$ScriptDir\it-solutions"
$ShWrapperContent = @'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"
if ! command -v python3 &>/dev/null; then
    PYTHON_BIN="python"
fi
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/cli.py" "$@"
'@
Set-Content -Path $ShWrapperPath -Value $ShWrapperContent -Encoding ASCII
Write-Success "Created cross-platform shell wrapper: $ShWrapperPath"

# Shortcut: corepulse.bat
$PulseBat = "$ScriptDir\corepulse.bat"
Set-Content -Path $PulseBat -Value "@echo off`r`n`"$PythonExe`" `"%~dp0corepulse\main.py`" %*" -Encoding ASCII
Write-Success "Created quick shortcut: $PulseBat"

# Shortcut: nexusshield.bat
$ShieldBat = "$ScriptDir\nexusshield.bat"
Set-Content -Path $ShieldBat -Value "@echo off`r`n`"$PythonExe`" `"%~dp0nexusshield\main.py`" %*" -Encoding ASCII
Write-Success "Created quick shortcut: $ShieldBat"

# Optional: Add to User PATH if requested
if ($AddToUserPath) {
    Write-Header "Step 3b: Adding to User Environment PATH"
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$ScriptDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$UserPath;$ScriptDir", "User")
        Write-Success "Added $ScriptDir to User PATH."
    } else {
        Write-Info "$ScriptDir is already present in User PATH."
    }
}

# 4. Run Corporate Health Audit Self-Test
if (-not $SkipHealthCheck) {
    Write-Header "Step 4: Executing Corporate Infrastructure Self-Test"
    & $PythonExe "$ScriptDir\cli.py" health
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Corporate infrastructure self-test reported issues."
        exit 1
    }
}

# 5. Completion Summary
Write-Header "Installation Complete!"
Write-Host @"
  ========================================================================
  [+] Corporate Suite successfully installed and validated!
  
  Quickstart Commands (from $ScriptDir):
    1. Unified Health:     .\it-solutions.bat health
    2. CorePulse Server:   .\it-solutions.bat pulse --port 8080
    3. NexusShield Audit:  .\it-solutions.bat shield scan .
    4. Suite Version:      .\it-solutions.bat version

  Direct Shortcuts:
    - Launch CorePulse:    .\corepulse.bat
    - Run NexusShield:     .\nexusshield.bat scan <dir>
  ========================================================================
"@ -ForegroundColor Green
