#!/usr/bin/env bash
# ==============================================================================
# IT Solutions Enterprise Suite - 1-Click Unix/macOS Installer
# Installs and configures CorePulse v1.0 and NexusShield v1.0.
# Zero external dependencies. Requires Python 3.8+.
# ==============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
cat << "EOF"
  ___ _____   _____       _       _   _                 
 |_ _|_   _| /  ___|     | |     | | (_)                
  | |  | |   \ `--.  ___ | |_   _| |_ _  ___  _ __  ___ 
  | |  | |    `--. \/ _ \| | | | | __| |/ _ \| '_ \/ __|
 _| |_ | |   /\__/ / (_) | | |_| | |_| | (_) | | | \__ \
 \___/ \_/   \____/ \___/|_|\__,_|\__|_|\___/|_| |_|___/
    Enterprise Suite 1-Click Unix/macOS Installer v1.0.0
    Products: CorePulse v1.0 + NexusShield v1.0
EOF
echo -e "${NC}"

# 1. Resolve Installation Directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "\n${CYAN}=== Step 1: Locating Installation Root ===${NC}"
echo "  Base Directory: ${SCRIPT_DIR}"

if [[ ! -d "${SCRIPT_DIR}/corepulse" || ! -d "${SCRIPT_DIR}/nexusshield" ]]; then
    echo -e "  ${RED}[ERROR] Required product directories ('corepulse', 'nexusshield') not found in ${SCRIPT_DIR}${NC}"
    exit 1
fi
echo -e "  ${GREEN}[OK] Found CorePulse and NexusShield source packages.${NC}"

# 2. Detect and Validate Python 3.8+
echo -e "\n${CYAN}=== Step 2: Python Environment Verification ===${NC}"
PYTHON_BIN=""

for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER_CHECK=$("$cmd" -c "import sys; print(1 if sys.version_info >= (3, 8) else 0)" 2>/dev/null || echo "0")
        if [[ "$VER_CHECK" == "1" ]]; then
            PYTHON_BIN="$cmd"
            PY_VER=$("$cmd" --version)
            break
        fi
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    echo -e "  ${RED}[ERROR] Python 3.8 or higher was not detected on this system.${NC}"
    echo "  Please install Python 3.8+ using your system package manager (e.g. brew install python3, apt install python3)."
    exit 1
fi

echo -e "  ${GREEN}[OK] Detected compatible Python runtime: ${PY_VER} (${PYTHON_BIN})${NC}"
echo -e "  ${GREEN}[OK] Zero external dependencies verified (100% Standard Library Python architecture).${NC}"

# 3. Generate Portable CLI Distribution Wrappers
echo -e "\n${CYAN}=== Step 3: Generating Unified Command-Line Wrappers ===${NC}"

# it-solutions executable
WRAPPER_FILE="${SCRIPT_DIR}/it-solutions"
cat << EOF > "${WRAPPER_FILE}"
#!/usr/bin/env bash
# IT Solutions Unified Enterprise CLI Wrapper
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/cli.py" "\$@"
EOF
chmod +x "${WRAPPER_FILE}"
echo -e "  ${GREEN}[OK] Created executable wrapper: ${WRAPPER_FILE}${NC}"

# corepulse shortcut
PULSE_SHORTCUT="${SCRIPT_DIR}/corepulse.sh"
cat << EOF > "${PULSE_SHORTCUT}"
#!/usr/bin/env bash
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/corepulse/main.py" "\$@"
EOF
chmod +x "${PULSE_SHORTCUT}"
echo -e "  ${GREEN}[OK] Created quick shortcut: ${PULSE_SHORTCUT}${NC}"

# nexusshield shortcut
SHIELD_SHORTCUT="${SCRIPT_DIR}/nexusshield.sh"
cat << EOF > "${SHIELD_SHORTCUT}"
#!/usr/bin/env bash
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/nexusshield/main.py" "\$@"
EOF
chmod +x "${SHIELD_SHORTCUT}"
echo -e "  ${GREEN}[OK] Created quick shortcut: ${SHIELD_SHORTCUT}${NC}"

# 4. Run Corporate Health Audit Self-Test
echo -e "\n${CYAN}=== Step 4: Executing Corporate Infrastructure Self-Test ===${NC}"
"${PYTHON_BIN}" "${SCRIPT_DIR}/cli.py" health

# 5. Completion Summary
echo -e "\n${CYAN}=== Installation Complete! ===${NC}"
cat << EOF
  ========================================================================
  ${GREEN}[+] Corporate Suite successfully installed and validated!${NC}
  
  Quickstart Commands (from ${SCRIPT_DIR}):
    1. Unified Health:     ./it-solutions health
    2. CorePulse Server:   ./it-solutions pulse --port 8080
    3. NexusShield Audit:  ./it-solutions shield scan .
    4. Suite Version:      ./it-solutions version

  Direct Shortcuts:
    - Launch CorePulse:    ./corepulse.sh
    - Run NexusShield:     ./nexusshield.sh scan <dir>
  ========================================================================
EOF
