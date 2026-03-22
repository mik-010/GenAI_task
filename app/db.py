from sqlalchemy import create_engine

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)


def get_engine():
    return engine
