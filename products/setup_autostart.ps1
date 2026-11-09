<#
.SYNOPSIS
    CorePulse Omnibar Windows Workstation Autostart Manager (Sprint 12).
    Configures or removes background autostart of CorePulse Omnibar on Windows boot.

.DESCRIPTION
    Installs a user-level Windows Run key (HKCU:\Software\Microsoft\Windows\CurrentVersion\Run)
    pointing to pythonw.exe running 'products/corepulse/omnibar.py --daemon'.
    Ensures zero terminal window popup and instant availability of 'Ctrl+Shift+Space' hotkey on logon.

.PARAMETER Install
    Registers CorePulse Omnibar in Windows HKCU Startup Registry.

.PARAMETER Uninstall
    Removes CorePulse Omnibar from Windows Startup Registry.

.PARAMETER Status
    Displays current autostart registration state.
#>

[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorkspaceDir = Split-Path -Parent $ScriptDir
$OmnibarScript = Join-Path $ScriptDir "corepulse\omnibar.py"
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RegKeyName = "CorePulseOmnibar"

function Get-PythonwPath {
    # 1. Check active Python installation directory
    try {
        $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($pythonExe) {
            $pyDir = Split-Path -Parent $pythonExe
            $pythonw = Join-Path $pyDir "pythonw.exe"
            if (Test-Path $pythonw) {
                return $pythonw
            }
            return $pythonExe
        }
    } catch {}

    # 2. Check standard Windows user program locations
    $searchPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\pythonw.exe",
        "$env:ProgramFiles\Python3*\pythonw.exe",
        "C:\Python3*\pythonw.exe"
    )
    foreach ($pattern in $searchPaths) {
        $found = Resolve-Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            return $found.Path
        }
    }

    return "pythonw.exe"
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  CorePulse Omnibar Windows Workstation Autostart Manager" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

if (-not (Test-Path $OmnibarScript)) {
    Write-Error "Omnibar script not found at expected path: $OmnibarScript"
    exit 1
}

$CurrentVal = (Get-ItemProperty -Path $RegPath -Name $RegKeyName -ErrorAction SilentlyContinue).$RegKeyName

if ($Uninstall) {
    if ($CurrentVal) {
        Remove-ItemProperty -Path $RegPath -Name $RegKeyName -Force
        Write-Host "[OK] SUCCESS: CorePulse Omnibar autostart removed from Windows Registry." -ForegroundColor Green
    } else {
        Write-Host "[i] CorePulse Omnibar is not currently registered in autostart." -ForegroundColor Yellow
    }
    exit 0
}

if ($Install -or (-not $Status -and -not $Uninstall)) {
    $Pythonw = Get-PythonwPath
    $TargetCmd = "`"$Pythonw`" `"$OmnibarScript`" --daemon"

    Set-ItemProperty -Path $RegPath -Name $RegKeyName -Value $TargetCmd -Force
    Write-Host "[OK] SUCCESS: CorePulse Omnibar registered for Windows logon autostart!" -ForegroundColor Green
    Write-Host "    - Registry Key: $RegPath\$RegKeyName" -ForegroundColor Gray
    Write-Host "    - Executable:   $Pythonw" -ForegroundColor Gray
    Write-Host "    - Target File:  $OmnibarScript" -ForegroundColor Gray
    Write-Host "    - Hotkey:       Ctrl + Shift + Space (Active on every boot)" -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

# Status query
Write-Host "Autostart Registration Status:" -ForegroundColor White
if ($CurrentVal) {
    Write-Host "  - State:   [INSTALLED & ACTIVE]" -ForegroundColor Green
    Write-Host "  - Command: $CurrentVal" -ForegroundColor Gray
} else {
    Write-Host "  - State:   [NOT INSTALLED]" -ForegroundColor Yellow
    Write-Host "  - Hint:    Run with -Install to configure 1-click boot launch." -ForegroundColor Gray
}
Write-Host "=================================================================" -ForegroundColor Cyan
