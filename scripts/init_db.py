#!/usr/bin/env python3
"""Initialize the VNA SQLite database with all required tables and indexes."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from backend.db.database import init_db
from backend.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("init_db")


def main() -> None:
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    logger.info("Initializing VNA database...")
    init_db(db_path)
    logger.info("Database initialization complete.")


if __name__ == "__main__":
    main()
