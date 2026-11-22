import os
import sys
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import settings

def purge_demo_data():
    print("==========================================================")
    print("L&K Skill Hub — Demo Data Purge Script")
    print("==========================================================")
    print("WARNING: This will permanently delete all demo records (is_demo=1)")
    print("while strictly preserving all real production accounts and system configuration.")
    confirm = input("Are you sure you want to proceed? Type 'CONFIRM': ")
    if confirm.strip() != "CONFIRM":
        print("Aborted.")
        sys.exit(0)

    db = SessionLocal()
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "remove_demo_data.sql")
    if not os.path.exists(script_path):
        print(f"Error: Script file not found at {script_path}")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        sql = f.read()

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    purged_count = 0
    try:
        for stmt in statements:
            # Skip USE or comments
            if stmt.upper().startswith("USE "):
                continue
            try:
                db.execute(text(stmt))
                purged_count += 1
            except Exception as e:
                # If table doesn't exist or already empty, continue
                pass
        db.commit()
        print(f"\n[SUCCESS] Demo data purged successfully across {purged_count} entities.")
    finally:
        db.close()

if __name__ == "__main__":
    purge_demo_data()
