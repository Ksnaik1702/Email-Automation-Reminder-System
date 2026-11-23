"""
Root Launcher for Background Worker.
Usage:
    python worker.py                       # Runs continuous worker in safe SIMULATION mode (default)
    python worker.py --once                # Runs a single evaluation cycle in simulation mode
    python worker.py --live --confirm-live # Runs continuous worker in LIVE SMTP delivery mode
    python worker.py --once --live --confirm-live  # Single cycle in LIVE SMTP delivery mode
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
