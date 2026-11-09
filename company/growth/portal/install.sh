#!/usr/bin/env bash
# ==============================================================================
# IT Solutions Global Corporation — Turnkey POSIX Workstation Installer
# Installs CorePulse, NexusShield, and EchoStream in <10 seconds.
# 100% Python Standard Library. Zero Bloat. 100% Offline Private Compute.
# Usage: curl -fsSL https://it-solutions-global.vercel.app/install.sh | bash
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================================================${NC}"
echo -e "${WHITE}         IT SOLUTIONS GLOBAL — AUTONOMOUS ENTERPRISE TRIAD INSTALLER        ${NC}"
echo -e "${GRAY}            CorePulse (Action) • NexusShield (Defense) • EchoStream (Perception)   ${NC}"
echo -e "${CYAN}============================================================================${NC}"
echo ""

# 1. Detect Python 3
echo -e "${YELLOW}[1/3] Verifying Python 3 runtime environment...${NC}"
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "\033[0;31m[ERROR] Python 3.9+ is required. Please install python3 and re-run.${NC}"
    exit 1
fi

PY_VER=$($PYTHON_CMD --version)
echo -e "${GREEN}  [OK] Found $PY_VER ($PYTHON_CMD)${NC}"

# 2. Install / Upgrade it-solutions-suite
echo -e "${YELLOW}[2/3] Installing it-solutions-suite from PyPI...${NC}"
$PYTHON_CMD -m pip install --upgrade it-solutions-suite --quiet --disable-pip-version-check
echo -e "${GREEN}  [OK] it-solutions-suite installed successfully.${NC}"

# 3. Launch CorePulse Engine & Open Cockpit
echo -e "${YELLOW}[3/3] Launching CorePulse Engine daemon on http://127.0.0.1:8080...${NC}"
if ! curl -s --max-time 1 http://127.0.0.1:8080/api/health | grep -q "healthy"; then
    nohup $PYTHON_CMD -m corepulse.main >/dev/null 2>&1 &
    sleep 2
fi

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${WHITE}  [SUCCESS] IT SOLUTIONS SUITE IS LIVE ON YOUR WORKSTATION!                ${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo -e "${CYAN}  • Cockpit UI:     http://127.0.0.1:8080${NC}"
echo -e "${CYAN}  • REST API:       http://127.0.0.1:8080/api/health${NC}"
echo -e "${GRAY}  • Local Data:     100% private SQLite WAL store${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""

# Open browser if possible
if command -v xdg-open &>/dev/null; then
    xdg-open "http://127.0.0.1:8080" &>/dev/null &
elif command -v open &>/dev/null; then
    open "http://127.0.0.1:8080" &>/dev/null &
fi
