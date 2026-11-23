"""
Root Launcher for Background Worker.
Usage:
    python worker.py           # Runs continuous background worker loop
    python worker.py --once    # Runs a single evaluation cycle and exits
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.worker import main

if __name__ == "__main__":
    main()
