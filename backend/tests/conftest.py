import os
import pytest
import pymysql
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import app.core.database as app_db
from app.models.phase13_models import SSOConfiguration
from app.seed import init_db
from app.seed_phase7 import seed_phase7_data

TEST_DB_NAME = "skillhub_test_db"

if "mysql" in settings.DATABASE_URL:
    try:
        @event.listens_for(app_db.engine, "connect")
        def set_isolation_level(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cursor.close()
            except Exception:
                pass
    except Exception:
        pass

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create a completely fresh MySQL test database for the entire test session."""
    target_url = settings.DATABASE_URL
    if "mysql" in target_url:
        conn = pymysql.connect(host="127.0.0.1", user="root", password="root", autocommit=True)
        cur = conn.cursor()
        cur.execute("SET GLOBAL TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        cur.execute(f"DROP DATABASE IF EXISTS `{TEST_DB_NAME}`;")
        cur.execute(f"CREATE DATABASE `{TEST_DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.select_db(TEST_DB_NAME)
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        def strip_comments(sql: str) -> str:
            lines = [l for l in sql.splitlines() if not l.strip().startswith("--")]
            return "\n".join(lines).strip()

        # Load schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "database", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            for stmt in f.read().split(";"):
                sql_cmd = strip_comments(stmt)
                if not sql_cmd:
                    continue
                if sql_cmd.upper().startswith("CREATE DATABASE") or sql_cmd.upper().startswith("USE "):
                    continue
                cur.execute(sql_cmd)

        # Load seed.sql
        seed_path = os.path.join(os.path.dirname(__file__), "..", "..", "database", "seed.sql")
        with open(seed_path, "r", encoding="utf-8") as f:
            for stmt in f.read().split(";"):
                sql_cmd = strip_comments(stmt)
                if not sql_cmd:
                    continue
                if sql_cmd.upper().startswith("CREATE DATABASE") or sql_cmd.upper().startswith("USE "):
                    continue
                cur.execute(sql_cmd)

        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.close()

        # Seed Phase 7 coding data and default SSO configuration
        if "mysql" in target_url:
            app_db.engine = app_db.engine.execution_options(isolation_level="READ COMMITTED")
            app_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_db.engine)

        init_db()
        seed_phase7_data()

        yield
    else:
        clean_url = target_url.strip("\"'")
        if "sqlite:///" in clean_url:
            db_file = clean_url.replace("sqlite:///", "")
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except Exception:
                    pass
        from app.core.database import Base
        Base.metadata.create_all(bind=app_db.engine)
        init_db()
        seed_phase7_data()
        yield


@pytest.fixture(autouse=True)
def reset_mutable_test_state():
    """Ensure mutable global configurations like allow_local_login are reset after each test."""
    yield
    try:
        db = app_db.SessionLocal()
        conf = db.query(SSOConfiguration).first()
        if conf and not conf.allow_local_login:
            conf.allow_local_login = True
            db.commit()
        db.close()
    except Exception:
        pass
