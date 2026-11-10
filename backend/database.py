import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("handoverledger.database")

def create_app_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
            future=True,
            echo=False
        )

    # PostgreSQL / Cloud Databases
    try:
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=300,
            future=True,
            echo=False
        )
    except Exception as e:
        # If default postgresql dialect failed to find driver, try alternate driver schemes
        if "postgresql://" in url:
            for alt_driver in ["postgresql+psycopg2://", "postgresql+psycopg://"]:
                try:
                    alt_url = url.replace("postgresql://", alt_driver, 1)
                    return create_engine(
                        alt_url,
                        pool_pre_ping=True,
                        pool_recycle=300,
                        future=True,
                        echo=False
                    )
                except Exception:
                    continue
        logger.error(f"Failed to initialize database engine for URL scheme: {e}")
        raise e

db_url = settings.effective_database_url
engine = create_app_engine(db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
