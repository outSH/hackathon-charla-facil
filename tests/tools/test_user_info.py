import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from charla_facil.storage import db
from charla_facil.storage.orm_models import Base, UserProfileORM
from charla_facil.tools.user_info import (
    UserHistoryEvent,
    UserInfoUpdate,
    save_user_info,
    get_user_info,
)


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """
    Replaces the global engine with an in-memory SQLite engine.
    Ensures tests are isolated and have a clean DB each time.
    """
    test_engine = create_engine("sqlite:///:memory:", echo=False)

    # Create schema
    Base.metadata.create_all(test_engine)

    # Monkeypatch the production get_engine() func
    # Monkeypatch get_db_engine()
    monkeypatch.setattr(db, "_db", test_engine)

    monkeypatch.setattr(db, "get_db_engine", lambda: test_engine)

    # Insert the single initial profile row
    with Session(test_engine) as session:
        session.add(UserProfileORM(id=1))
        session.commit()

    yield


def test_happy_path_save_and_retrieve():
    update = UserInfoUpdate(
        name="Alice",
        cefr_level="A2",
        nationality="Wonderland",
        age=25,
        place_of_living="Looking Glass",
        interests=["tea", "chess"],
        new_events=[
            UserHistoryEvent(name="Met the White Rabbit", date="2023-01-01")
        ]
    )

    result = save_user_info(update)

    assert result.status == "success"
    assert "name" in result.updated_fields
    assert "cefr_level" in result.updated_fields
    assert "nationality" in result.updated_fields
    assert "age" in result.updated_fields
    assert "place_of_living" in result.updated_fields
    assert "interests" in result.updated_fields
    assert "new_events" in result.updated_fields

    profile = get_user_info()
    assert profile.name == "Alice"
    assert profile.cefr_level == "A2"
    assert profile.nationality == "Wonderland"
    assert profile.age == 25
    assert profile.place_of_living == "Looking Glass"
    assert profile.interests == ["tea", "chess"]
    assert len(profile.recent_events) == 1
    assert profile.recent_events[0].name == "Met the White Rabbit"


def test_overwriting_works():
    save_user_info(UserInfoUpdate(
        name="Alice",
        interests=["tea", "chess"],
    ))

    # Overwrite with new values
    result = save_user_info(UserInfoUpdate(
        name="Alice Updated",
        interests=["cards"],  # overwrite list
    ))

    assert result.status == "success"
    assert "name" in result.updated_fields
    assert "interests" in result.updated_fields

    profile = get_user_info()
    assert profile.name == "Alice Updated"
    assert profile.interests == ["cards"]  # fully replaced


def test_duplicate_events_not_added_and_error_raised():
    first = UserInfoUpdate(
        new_events=[
            UserHistoryEvent(
                name="Event1",
                date="2024-01-01"
            )
        ]
    )
    # First insert succeeds
    save_user_info(first)

    # Try to add duplicate event
    second = UserInfoUpdate(
        new_events=[
            UserHistoryEvent(
                name="Event1",
                date="2024-01-01"
            )
        ]
    )
    # We expect IntegrityError inside save_user_info
    with pytest.raises(Exception):
        save_user_info(second)

    # Verify only one event exists
    profile = get_user_info(None)
    assert len(profile.recent_events) == 1
    assert profile.recent_events[0].name == "Event1"
