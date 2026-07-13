#!/usr/bin/env python3
"""Create/refresh the database schema. Run: python scripts/setup_db.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import setup_database

if __name__ == "__main__":
    setup_database()
