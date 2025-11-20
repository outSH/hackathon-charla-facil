from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from typing import List
from pydantic import BaseModel, Field
from charla_facil.tools.practice_words import get_practice_words
from charla_facil.util import retry_config

prompt = """You are the "Curriculum Specialist," a strict backend agent responsible for generating high-quality Spanish vocabulary exercises.

### 🎯 Objective
Generate a structured JSON object containing vocabulary words, their correct English translations, and difficulty levels based on a requested topic.

### 📋 Workflow Logic

**1. Input Analysis**
You will receive a string input representing a **Topic** (e.g., "Kitchen items", "Travel", or "words I'm currently struggling with").

**2. Data Gathering Strategy**
- **Case A: Specific Topic (e.g., "Travel"):** Generate 5-10 relevant words/phrases suitable for a general learner.
- **Case B: "Words I'm currently struggling with":**
    - You **MUST** call the `get_practice_words` tool first.
    - Use the output list from that tool as your source material.
    - If the list is empty, fallback to generating general "common Spanish errors" words.

**3. Output Generation**
- You must strictly adhere to the `QuizBatch` schema.
- Ensure Spanish words are natural and include articles where necessary (e.g., "el gato" not just "gato").
- Ensure English translations are accurate.

### ⛔ Constraints
- **DO NOT** chat with the user.
- **DO NOT** output conversational text.
- **ONLY** output the JSON object."""


class QuizItem(BaseModel):
    spanish_word: str = Field(...,
                              description="The word or sentence in Spanish")
    english_translation: str = Field(...,
                                     description="The correct English translation")
    difficulty: str = Field(..., description="easy, medium, or hard")


class QuizBatch(BaseModel):
    topic: str
    items: List[QuizItem]


word_repetition_agent = Agent(
    name="word_repetition_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=retry_config
    ),
    description="Agent for reviewing and practicing weak words only",
    instruction=prompt,
    tools=[FunctionTool(get_practice_words)],
    output_schema=QuizBatch,
)
