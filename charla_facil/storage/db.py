import os
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from charla_facil.storage.orm_models import Base, UserProfileORM

DB_PATH = os.getenv("DB_PATH", "default.db")
_db = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# Create schema if missing
if not os.path.exists(DB_PATH):
    Base.metadata.create_all(_db)


# Ensure a single profile row exists for default user
with Session(_db) as session:
    if not session.scalar(select(UserProfileORM)):
        session.add(UserProfileORM(id=1))
        session.commit()


def get_db_engine():
    return _db
