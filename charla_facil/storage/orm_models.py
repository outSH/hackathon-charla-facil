from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


# ============================================================
#  User Profile Models
# ============================================================


class UserProfileORM(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    cefr_level = Column(String, nullable=True)
    name = Column(String, nullable=True)
    nationality = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    place_of_living = Column(String, nullable=True)

    # Relationships (interests + events)
    interests = relationship("UserInterestORM", cascade="all, delete-orphan")
    events = relationship("UserEventORM", cascade="all, delete-orphan")


class UserInterestORM(Base):
    __tablename__ = "user_interest"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"))
    interest = Column(String, nullable=False)


class UserEventORM(Base):
    __tablename__ = "user_event"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"))
    name = Column(String, nullable=False)
    date = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name", "date", name="uq_user_event"),
    )


# ============================================================
#  PracticeWord Models
# ============================================================


class PracticeWordORM(Base):
    __tablename__ = "practice_word"

    word = Column(String, primary_key=True)
    familiarity_level = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=False, default=datetime.now)
    correct_streak_count = Column(Integer, nullable=False, default=0)
    update_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint('familiarity_level >= 0 AND familiarity_level <= 100',
                        name='ck_familiarity_level_range'),
    )
