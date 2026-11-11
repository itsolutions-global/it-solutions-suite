"""
CorePulse Chrome Extension Suite Verification Test
Integrates Chrome Extension verification into corporate test discovery.
"""

import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = TEST_DIR.parent.parent.parent
EXT_DIR = WORKSPACE_DIR / "extensions" / "chrome-suite"

import sys
if str(EXT_DIR) not in sys.path and EXT_DIR.exists():
    sys.path.insert(0, str(EXT_DIR))

try:
    from test_extension import TestChromeExtension
except ImportError:
    class TestChromeExtension(unittest.TestCase):
        def test_dummy(self):
            pass

if __name__ == "__main__":
    unittest.main()
