from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from charla_facil.storage import db
from charla_facil.storage.orm_models import PracticeWordORM, Base
from charla_facil.tools.practice_words import (
    PracticeWordSchema,
    get_practice_words,
    update_practice_words,
    WordCorrectness,
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

    # Monkeypatch db.get_db_engine()
    monkeypatch.setattr(db, "_db", test_engine)

    monkeypatch.setattr(db, "get_db_engine", lambda: test_engine)

    yield


def get_word(session, word):
    return session.get(PracticeWordORM, word)


def test_correct_word_sets_high_familiarity():
    update_practice_words([
        {"word": "gato", "correctness": WordCorrectness.PERFECT}
    ])

    with Session(db.get_db_engine()) as s:
        w = get_word(s, "gato")
        assert w is not None
        # initial_familiarity(4) = 10 + 4*15 = 70
        assert w.familiarity_level == 70


def test_incorrect_word_sets_low_familiarity():
    update_practice_words([
        {"word": "perro", "correctness": WordCorrectness.DID_NOT_KNOW}
    ])

    with Session(db.get_db_engine()) as s:
        w = get_word(s, "perro")
        assert w is not None
        # initial_familiarity(0) = 10 + 0 = 10
        assert w.familiarity_level == 10


def test_good_correctness_increases_familiarity():
    # First add the word with low familiarity
    update_practice_words([
        {"word": "comer", "correctness": WordCorrectness.DID_NOT_KNOW}
    ])

    with Session(db.get_db_engine()) as s:
        before = get_word(s, "comer").familiarity_level

    # Now use it correctly (3 or 4)
    update_practice_words([
        {"word": "comer", "correctness": WordCorrectness.PERFECT}
    ])

    with Session(db.get_db_engine()) as s:
        after = get_word(s, "comer").familiarity_level

    assert after > before


def test_bad_correctness_decreases_familiarity():
    # Create word with high familiarity
    update_practice_words([
        {"word": "leer", "correctness": WordCorrectness.PERFECT}
    ])
    update_practice_words([
        {"word": "leer", "correctness": WordCorrectness.PERFECT}
    ])

    with Session(db.get_db_engine()) as s:
        before = get_word(s, "leer").familiarity_level
        assert before > 60  # sanity check: should be high-ish

    # Incorrect use should drop familiarity
    update_practice_words([
        {"word": "leer", "correctness": WordCorrectness.DID_NOT_KNOW}
    ])

    with Session(db.get_db_engine()) as s:
        after = get_word(s, "leer").familiarity_level

    assert after < before


def test_repeated_correctness_does_not_exceed_100():
    word = "hablar"

    # First observation
    update_practice_words([
        {"word": word, "correctness": WordCorrectness.PERFECT}
    ])

    # Repeat many times
    for _ in range(50):
        update_practice_words([
            {"word": word, "correctness": WordCorrectness.PERFECT}
        ])

    with Session(db.get_db_engine()) as s:
        w = get_word(s, word)

    assert 0 <= w.familiarity_level <= 100
    assert w.familiarity_level == 100  # should converge to 100 but not exceed it


def test_repeated_low_correctness_does_not_go_below_zero():
    word = "vivir"

    # First observation - start somewhere >0
    update_practice_words([
        {"word": word, "correctness": WordCorrectness.PERFECT}
    ])

    # Now repeatedly bad uses
    for _ in range(50):
        update_practice_words([
            {"word": word, "correctness": WordCorrectness.DID_NOT_KNOW}
        ])

    with Session(db.get_db_engine()) as s:
        w = get_word(s, word)

    assert 0 <= w.familiarity_level <= 100
    assert w.familiarity_level == 0  # should bottom out at 0


def test_get_top_practice_words():
    # Prepare 6 words with varying familiarity, update_count, last_used
    now = datetime.now()
    words_data = [
        {"word": "uno", "familiarity_level": 50, "update_count": 3,
            "last_used": now - timedelta(days=5)},
        {"word": "dos", "familiarity_level": 10, "update_count": 1,
            "last_used": now - timedelta(days=10)},
        {"word": "tres", "familiarity_level": 80, "update_count": 0,
            "last_used": now - timedelta(days=2)},
        {"word": "cuatro", "familiarity_level": 20,
            "update_count": 2, "last_used": now - timedelta(days=15)},
        {"word": "cinco", "familiarity_level": 70,
            "update_count": 1, "last_used": now - timedelta(days=1)},
        {"word": "seis", "familiarity_level": 5, "update_count": 0,
            "last_used": now - timedelta(days=20)},
    ]

    # Insert into DB
    with Session(db.get_db_engine()) as session:
        for wd in words_data:
            session.add(PracticeWordORM(**wd))
        session.commit()

    # Fetch top 3 words for practice
    top_words_json = get_practice_words(count=3)

    # Convert JSON strings back to dicts for assertions
    top_words = [PracticeWordSchema.model_validate(w) for w in top_words_json]

    # Expected order:
    # struggle (low familiarity) descending → six(5), dos(10), cuatro(20)
    expected_order = ["seis", "dos", "cuatro"]
    actual_order = [w.word for w in top_words]

    assert actual_order == expected_order
