from enum import IntEnum
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from charla_facil.storage.db import get_db_engine
from charla_facil.storage.orm_models import PracticeWordORM


class WordCorrectness(IntEnum):
    """Scoring scale for how correctly a user used a Spanish word."""
    DID_NOT_KNOW = 0           # did not know it
    COMPLETELY_WRONG = 1       # used in completely wrong context
    SOMEWHAT_WRONG = 2         # used in somewhat wrong context
    GOOD_BUT_MISSPELLED = 3    # used in good context but misspelled
    PERFECT = 4                # all good


# Mapping correctness -> target familiarity (0..100)
TARGET_BY_CORRECTNESS = {
    0: 0,
    1: 10,
    2: 40,
    3: 70,
    4: 100
}

# Base learning rates per correctness (asymmetric: bad -> faster)
BASE_LR_BY_CORRECTNESS = {
    0: 0.60,
    1: 0.40,
    2: 0.25,
    3: 0.12,
    4: 0.08
}


def initial_familiarity(correctness: int) -> int:
    """
    Compute initial familiarity for a word when first observed.
    """

    value = 10 + correctness * 15
    return max(0, min(100, int(round(value))))


# Streak multiplier configuration for consecutive good uses.
# For each extra consecutive "good" use, multiply lr by (1 + STREAK_STEP)
STREAK_STEP = 0.12     # +12% lr per additional consecutive good use
# don't grow lr above (1 + STREAK_MAX_BONUS) times base
STREAK_MAX_BONUS = 0.60


class WordUpdate(BaseModel):
    word: str = Field(
        ...,
        description="The specific Spanish word to track (e.g., 'gato', 'correr')."
    )
    correctness: int = Field(
        ...,
        description=(
            "How accurately the user used the word. "
            "0 = did not know it, "
            "1 = completely wrong, "
            "2 = somewhat wrong, "
            "3 = correct context but misspelled, "
            "4 = perfect."
        )
    )


def update_practice_words(updates: List[WordUpdate]) -> None:
    """
    The core feedback loop. Updates the database with the user's proficiency on specific words used in the current message.

    Usage: Call this after every user message containing Spanish.

    Correctness Grading Scale:

    - 0: User didn't know the word.
    - 1: Completely wrong use.
    - 2: Semantic error.
    - 3: Typo / minor grammatical error.
    - 4: Perfect usage.

    Args:
        updates: A list of WordUpdate objects containing the word and a correctness rating.

    """

    for update in updates:
        item = WordUpdate(**update)
        correctness = item.correctness
        word = item.word.lower().strip()
        current_time = datetime.now()

        with Session(get_db_engine()) as session:
            saved_word = session.get(PracticeWordORM, word)

            if saved_word:
                is_good = correctness >= 3
                target = TARGET_BY_CORRECTNESS[correctness]
                base_lr = BASE_LR_BY_CORRECTNESS[correctness]

                if is_good:
                    saved_word.correct_streak_count = saved_word.correct_streak_count + 1
                    bonus = min(STREAK_MAX_BONUS, STREAK_STEP *
                                (saved_word.correct_streak_count - 1))
                    lr = base_lr * (1.0 + bonus)
                else:
                    saved_word.correct_streak_count = 0
                    lr = base_lr

                old = saved_word.familiarity_level
                new = old + lr * (target - old)

                if abs(new - old) < 1.0:
                    new = target

                saved_word.familiarity_level = int(
                    round(max(0, min(100, new)))
                )

                session.add(saved_word)
            else:
                session.add(PracticeWordORM(
                    word=word, familiarity_level=initial_familiarity(correctness), last_used=current_time))

            session.commit()


class PracticeWordSchema(BaseModel):
    """
    Pydantic schema for a practice word.
    Converts SQLAlchemy ORM model to JSON-friendly dict.
    """

    model_config = ConfigDict(from_attributes=True)

    word: str = Field(
        ...,
        description="The infinitive Spanish word (e.g., 'estar', 'gustar')."
    )
    familiarity_level: int = Field(
        ...,
        ge=0,
        le=100,
        description="User's familiarity with the word, integer in [0, 100]. "
                    "0 = completely unknown, 100 = fully mastered."
    )
    last_used: datetime = Field(
        ...,
        description="Timestamp of the last time this word was practiced."
    )
    correct_streak_count: int = Field(
        ...,
        ge=0,
        description="Number of consecutive successful uses of this word."
    )
    update_count: int = Field(
        ...,
        ge=0,
        description="Total number of times this word has been updated/practiced."
    )


def get_practice_words(count: int = 10) -> List[PracticeWordSchema]:
    """
    Retrieves a list of Spanish words the user has historically struggled with, sorted by "struggle level" (hardest first).

    Usage: Use this to find words to quiz the user on, or to weave difficult words into conversation for spaced repetition.

    Returns:
        A list of dictionaries containing word details.
    """

    words_query = (
        select(PracticeWordORM)
        .order_by(
            asc(PracticeWordORM.familiarity_level),
            asc(PracticeWordORM.update_count),
            asc(PracticeWordORM.last_used),
        )
        .limit(count)
    )

    with Session(get_db_engine()) as session:
        words = session.scalars(words_query).all()
        return [PracticeWordSchema.model_validate(w).model_dump() for w in words]
