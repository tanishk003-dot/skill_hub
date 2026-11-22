import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "skillhub.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"No DB found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check question_bank columns
    cursor.execute("PRAGMA table_info(question_bank);")
    existing_cols = [row[1] for row in cursor.fetchall()]

    new_qb_cols = [
        ("problem_statement", "TEXT"),
        ("allowed_languages", "JSON"),
        ("starter_code", "JSON"),
        ("sample_test_cases", "JSON"),
        ("hidden_test_cases", "JSON"),
        ("time_limit_sec", "FLOAT DEFAULT 2.0"),
        ("memory_limit_mb", "INTEGER DEFAULT 256")
    ]

    for col_name, col_type in new_qb_cols:
        if col_name not in existing_cols:
            print(f"Adding column {col_name} to question_bank...")
            cursor.execute(f"ALTER TABLE question_bank ADD COLUMN {col_name} {col_type};")

    # Check users columns
    cursor.execute("PRAGMA table_info(users);")
    user_cols = [row[1] for row in cursor.fetchall()]

    new_user_cols = [
        ("last_splash_date", "VARCHAR(20)"),
        ("fresh_login", "BOOLEAN DEFAULT 0")
    ]

    for col_name, col_type in new_user_cols:
        if col_name not in user_cols:
            print(f"Adding column {col_name} to users...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")

    conn.commit()
    conn.close()
    print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
