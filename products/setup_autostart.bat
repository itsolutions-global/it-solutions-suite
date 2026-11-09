@echo off
REM ==============================================================================
REM  CorePulse Omnibar 1-Click Windows Workstation Autostart Setup (Sprint 12)
REM  Zero dependencies. Configures background hotkey (Ctrl+Shift+Space) on logon.
REM ==============================================================================
title CorePulse Omnibar Autostart Manager
color 0B
cls

echo ==============================================================================
echo   CorePulse Omnibar Desktop Quick-Capture Autostart Setup
echo   Unified Corporate Suite | IT Solutions Global Corporation
echo ==============================================================================
echo.
echo   [1] Install Omnibar Autostart on Windows Logon (Recommended)
echo   [2] Uninstall / Remove Omnibar from Windows Startup
echo   [3] Check Current Autostart Registration Status
echo   [4] Launch Omnibar Daemon Now (Background)
echo   [5] Exit
echo.
echo ==============================================================================
set /p OPTION="Select an option [1-5]: "

if "%OPTION%"=="1" goto install
if "%OPTION%"=="2" goto uninstall
if "%OPTION%"=="3" goto status
if "%OPTION%"=="4" goto launch
if "%OPTION%"=="5" goto end

echo Invalid option selected.
pause
goto end

:install
echo.
echo [*] Configuring Windows Startup Registry...
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup_autostart.ps1" -Install
echo.
pause
goto end

:uninstall
echo.
echo [*] Removing Windows Startup Registry entry...
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup_autostart.ps1" -Uninstall
echo.
pause
goto end

:status
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup_autostart.ps1" -Status
echo.
pause
goto end

:launch
echo.
echo [*] Launching CorePulse Omnibar daemon (Ctrl+Shift+Space)...
start /b "" pythonw "%~dp0corepulse\omnibar.py" --daemon
echo [OK] Omnibar daemon launched in background.
echo Press Ctrl + Shift + Space anywhere in Windows to trigger capture!
echo.
pause
goto end

:end
exit /b 0
