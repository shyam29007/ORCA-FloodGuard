"""Script to initialize database tables and seed baseline Punjab data."""

import sys
from pathlib import Path

# Add project root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for p in [str(backend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.database.init_db import run_init

if __name__ == "__main__":
    print("Initializing ORAC-FloodGuard Database...")
    run_init()
    print("Database initialization and reference data seeding completed successfully.")

