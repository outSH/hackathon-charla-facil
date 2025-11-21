import logging
from google.genai import types
from google import genai
from google.adk.agents.callback_context import CallbackContext

from charla_facil.tools.practice_words import update_practice_words
from charla_facil.util import retry_config

logger = logging.getLogger(__name__)

_system_prompt = """You are a rigorous Linguistic Data Extractor. Your **only** function is to analyze Spanish language usage, extract words, grade them against a strict rubric, and execute the `update_practice_words` tool.

### 🔨 OPERATIONAL RULES (NON-NEGOTIABLE)

**1. EXECUTION MANDATE**
   - You MUST call `update_practice_words` exactly once per turn.
   - If no Spanish words or English fallbacks are present, call the function with an empty list `[]`.
   - **NO TEXT OUTPUT:** Do not generate conversational text. Return ONLY the function call.

**2. EXTRACTION & NORMALIZATION**
   - **Verbs:** Convert ALL conjugated verbs to their **Infinitive** form (e.g., "fui" -> "ir", "jugando" -> "jugar", "me lavo" -> "lavar").
   - **Nouns/Adjectives:** Convert to **Singular, Masculine** (unless the word is inherently feminine like "mujer"). (e.g., "casas" -> "casa", "rojas" -> "rojo").
   - **Ignore:** Proper nouns (Madrid, Juan), numbers, and non-linguistic fillers.

**3. GRADING RUBRIC (0-4)**
   - **Score 0 (Fallback/Unknown):** User wrote the word in ENGLISH because they didn't know the Spanish (e.g., "Quiero *apple*"). -> Save as Spanish "manzana" with Score 0.
   - **Score 0 (Wrong):** User used a Spanish word that makes no sense (e.g., "Soy *embarazada*" for "I am embarrassed").
   - **Score 1 (Semantic Fail):** Valid Spanish word, but wrong meaning for the context (e.g., "banco" (bank) when they meant "banco" (bench)).
   - **Score 2 (Grammar Fail):** Correct meaning, but wrong conjugation or gender agreement (e.g., "la gato", "yo comer").
   - **Score 3 (Minor Error):** Typo or missing accent (e.g., "cancion" vs "canción").
   - **Score 4 (Mastery):** Perfect semantics, grammar, and spelling.

### 🧪 EXAMPLES
* User: "Yo quiero eat una manzana."
    * Action: `[{"word": "querer", "correctness": 4}, {"word": "comer", "correctness": 0}, {"word": "manzana", "correctness": 4}]`
* User: "Las gatas son rojo."
    * Action: `[{"word": "gato", "correctness": 4}, {"word": "ser", "correctness": 4}, {"word": "rojo", "correctness": 2}]` (Agreement error on 'rojo')
"""

try:
    _client = genai.Client(http_options={"retry_options": retry_config})
except Exception as e:
    logger.error(
        f"Error initializing client: Ensure GEMINI_API_KEY environment variable is set.")
    logger.error(f"Details: {e}")
    exit()


def rate_word_use(user_message: str) -> None:
    """
    Analyzes the user's message and updates the word ratings.
    """

    if not user_message or not user_message.strip():
        return

    config = types.GenerateContentConfig(
        system_instruction=_system_prompt,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        ),
        tools=[update_practice_words],
    )

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=config,
        )

        if response.function_calls:
            function_call = response.function_calls[0]

            if function_call.name == update_practice_words.__name__:
                updates = function_call.args['updates']
                update_practice_words(updates)
                logger.info(
                    f"rate_word_use executed successfully for words: {updates}")
            else:
                logger.warning(
                    f"Model requested unknown function: {function_call.name}")
        else:
            logger.warning(
                "Model did not return a function call. Analysis skipped.")
    except Exception as e:
        logger.error(f"Linguistic analysis failed with Gemini API: {e}")


def rate_word_use_callback(callback_context: CallbackContext):
    user_message = callback_context.user_content
    if user_message and user_message.parts:
        rate_word_use(user_message.parts[0].text)
