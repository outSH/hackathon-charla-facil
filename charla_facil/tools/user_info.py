from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from charla_facil.storage.db import get_db_engine
from charla_facil.storage.orm_models import UserProfileORM, UserEventORM, UserInterestORM

# ============================================================
#  Pydantic Models
# ============================================================


class BaseUserAttributes(BaseModel):
    """Common attributes shared between updates and storage."""
    name: Optional[str] = Field(None, description="The user's preferred name")
    cefr_level: Optional[str] = Field(None, description="Student's CEFR proficiency level (A1/A2/B1/B2/C1/C2)")
    nationality: Optional[str] = Field(None, description="User's nationality")
    age: Optional[int] = Field(None, description="User's age in years")
    place_of_living: Optional[str] = Field(
        None, description="City/Country where user resides")
    interests: Optional[List[str]] = Field(
        None, description="List of current hobbies/interests")


class UserHistoryEvent(BaseModel):
    name: str = Field(..., description="Brief description of the event")
    date: str = Field(..., description="Date of event (YYYY-MM-DD)")


class UserInfoUpdate(BaseUserAttributes):
    """Model used by the LLM to send updates."""
    new_events: Optional[List[UserHistoryEvent]] = Field(
        None,
        description="List of NEW significant events to ADD to history."
    )


class UserProfile(BaseUserAttributes):
    """Full user profile returned to the agent."""
    recent_events: List[UserHistoryEvent] = Field(
        default_factory=list,
        description="History of last 10 significant events."
    )


class SaveUserResult(BaseModel):
    """Standardized success response for updates."""
    status: str
    updated_fields: List[str]
    message: str


# ============================================================
#  Tools
# ============================================================


def save_user_info(update_data: UserInfoUpdate) -> SaveUserResult:
    """
    Persists user details to the database.
    It handles partial updates (you can send just the fields that changed).

    Usage: Call this whenever the user mentions new personal details (e.g., "I moved to Madrid", "I like tennis", "I am level A2")

    Important: When adding history, only add new events.

    Returns:
      SaveUserResult with fields changed.
    """

    # Convert ADK dict inputs → Pydantic
    if isinstance(update_data, dict):
        try:
            model = UserInfoUpdate(**update_data)
        except ValidationError as e:
            return SaveUserResult(
                status="error",
                updated_fields=[],
                message=f"Validation failed: {e}"
            )
    else:
        model = update_data

    updated_fields = []

    with Session(get_db_engine()) as session:
        profile = session.scalar(
            select(UserProfileORM).where(UserProfileORM.id == 1))

        for field in BaseUserAttributes.model_fields.keys():
            value = getattr(model, field)
            if value is not None:
                if field == "interests":
                    # Replace interests table
                    profile.interests.clear()
                    for item in value:
                        profile.interests.append(
                            UserInterestORM(interest=item))
                else:
                    setattr(profile, field, value)

                updated_fields.append(field)

        if model.new_events:
            for ev in model.new_events:
                profile.events.append(
                    UserEventORM(
                        name=ev.name,
                        date=ev.date
                    )
                )
            updated_fields.append("new_events")

        session.add(profile)
        session.commit()

    return SaveUserResult(
        status="success",
        updated_fields=updated_fields,
        message=f"Successfully updated {len(updated_fields)} fields."
    )


def get_user_info(max_events: int = 10) -> UserProfile:
    """
    Retrieves the user's profile including name, age, nationality, CEFR level, interests, and recent conversation history events.

    Usage: Call this at the very beginning of every session to personalize the conversation or when in need to recall personal information about the user.

    Arguments:
      max_events (int): Maximum number of recent events to include in the result.
                        Defaults to 10. If set to None, returns ALL events.

    Returns:
      UserProfile model
    """

    with Session(get_db_engine()) as session:
        profile = session.scalar(
            select(UserProfileORM).where(UserProfileORM.id == 1))

        # Load interests
        interests = [row.interest for row in profile.interests]

        # Load events (ALL events kept in DB)
        events_query = (
            select(UserEventORM)
            .where(UserEventORM.user_id == profile.id)
            .order_by(UserEventORM.date.desc(), UserEventORM.id.desc())
        )

        # Apply LIMIT at the SQL level
        if max_events is not None:
            events_query = events_query.limit(max_events)

        selected_events = session.scalars(events_query).all()

        recent_events = [
            UserHistoryEvent(name=e.name, date=e.date)
            for e in selected_events
        ]

        return UserProfile(
            name=profile.name,
            cefr_level=profile.cefr_level,
            nationality=profile.nationality,
            age=profile.age,
            place_of_living=profile.place_of_living,
            interests=interests if interests else None,
            recent_events=recent_events
        )
