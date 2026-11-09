"""
CorePulse Omnibar Package Shim
Re-exports omnibar components for package-level imports.
"""

import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from omnibar import (
    GlobalHotkeyListener,
    OmnibarRouter,
    OmnibarUI,
    launch_daemon,
    launch_popup,
    main
)

__all__ = [
    "OmnibarRouter",
    "GlobalHotkeyListener",
    "OmnibarUI",
    "launch_daemon",
    "launch_popup",
    "main"
]
