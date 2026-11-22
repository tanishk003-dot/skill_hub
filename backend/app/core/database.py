import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

is_production = settings.APP_ENV.lower() == "production"
target_db_url = settings.DATABASE_URL

if is_production:
    if target_db_url.startswith("sqlite"):
        raise RuntimeError(
            "FATAL CONFIGURATION ERROR: In APP_ENV=production, SQLite is strictly prohibited. "
            "A production-ready MySQL 8 connection string must be configured in DATABASE_URL."
        )
    connect_args = {}
    try:
        engine = create_engine(target_db_url, connect_args=connect_args, pool_pre_ping=True)
        with engine.connect() as conn:
            pass
        logger.info("Successfully connected to production MySQL database.")
    except Exception as e:
        raise RuntimeError(
            f"FATAL: MySQL database is unreachable in production mode (DATABASE_URL={target_db_url}): {e}. "
            "Refusing to start."
        ) from e
else:
    # Development / Testing mode
    if target_db_url.startswith("mysql"):
        try:
            test_engine = create_engine(target_db_url, pool_pre_ping=True)
            with test_engine.connect() as conn:
                pass
            engine = test_engine
            logger.info("Connected to MySQL database in %s mode.", settings.APP_ENV)
        except Exception as e:
            logger.warning(
                "====================================================================\n"
                "WARNING: MySQL connection failed in %s mode (%s).\n"
                "Falling back to local SQLite database ('sqlite:///./skillhub.db') for local testing.\n"
                "====================================================================",
                settings.APP_ENV, e
            )
            connect_args = {"check_same_thread": False, "timeout": 30}
            engine = create_engine("sqlite:///./skillhub.db", connect_args=connect_args, pool_pre_ping=True)
    else:
        connect_args = {"check_same_thread": False, "timeout": 30} if target_db_url.startswith("sqlite") else {}
        engine = create_engine(target_db_url, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def DateTime6():
    """Return a DateTime column type that uses DATETIME(6) with microsecond precision on MySQL and DATETIME on SQLite."""
    from sqlalchemy import DateTime
    from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
    return DateTime().with_variant(MYSQL_DATETIME(fsp=6), "mysql")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
