"""
Local Ollama integration for text interpretation and explanation generation.
Ollama is used ONLY for:
- Interpreting workout free text into structured info
- Optionally clarifying ambiguous dish names
- Generating natural language explanations of recommendations

All numerical logic (calorie calculation, recommendations) is deterministic.
"""

import httpx
import json
import logging
import re

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:9b"


async def check_ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def get_available_models() -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


async def query_ollama(prompt: str, model: str | None = None, timeout: float = 300.0) -> str | None:
    """Send a prompt to local Ollama via chat API and return the response text."""
    model = model or DEFAULT_MODEL
    try:
        t = httpx.Timeout(10.0, read=timeout)
        async with httpx.AsyncClient(timeout=t) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.3, "num_predict": 512},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
            else:
                logger.warning(f"Ollama returned status {resp.status_code}: {resp.text}")
                return None
    except Exception as e:
        logger.warning(f"Ollama query failed: {type(e).__name__}: {e}")
        return None


def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from text that may contain reasoning around it."""
    # Try direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try code block
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Find first { ... } block
    m = re.search(r"\{[^{}]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


async def interpret_workout(raw_text: str, model: str | None = None) -> dict:
    """
    Use Ollama to interpret free-text workout description into structured data.
    Returns a dict with workout_type, and optionally refined duration/intensity.
    """
    prompt = f"""Analyze this workout description and extract structured information.
Return ONLY a JSON object with these fields:
- "workout_type": one of: running, jogging, cycling, swimming, walking, hiking, weight_training, strength, yoga, pilates, stretching, hiit, crossfit, elliptical, rowing, dancing, boxing, martial_arts, climbing, tennis, soccer, basketball, general, other
- "summary": a brief 1-sentence summary of the workout

Workout description: "{raw_text}"

Respond with ONLY the JSON object, no other text."""

    response = await query_ollama(prompt, model)
    if not response:
        return {"workout_type": "general", "summary": raw_text}

    result = _extract_json(response)
    if not result:
        return {"workout_type": "general", "summary": raw_text}

    valid_types = {
        "running", "jogging", "cycling", "swimming", "walking", "hiking",
        "weight_training", "strength", "yoga", "pilates", "stretching",
        "hiit", "crossfit", "elliptical", "rowing", "dancing", "boxing",
        "martial_arts", "climbing", "tennis", "soccer", "basketball",
        "general", "other",
    }
    if result.get("workout_type") not in valid_types:
        result["workout_type"] = "general"
    return result


async def generate_recommendation_explanation(
    recommendation: dict,
    profile: dict,
    model: str | None = None,
) -> str:
    """Generate a friendly natural language explanation of the daily recommendation."""
    prompt = f"""You are a friendly nutrition assistant. Write a brief, encouraging explanation (3-5 sentences) of today's meal recommendation.

Profile:
- Current weight: {profile.get('weight_kg')} kg, target: {profile.get('target_weight_kg')} kg
- Goal: {recommendation.get('goal', 'maintain weight')}

Today's recommendation:
- Calorie target: {recommendation.get('calorie_target')} kcal
- Activity calories burned: {recommendation.get('activity_calories', 0)} kcal
- Recommended dishes: {recommendation.get('recommended_dishes', 'not available')}
- Bread: {"yes" if recommendation.get('bread_recommended') else "not recommended"}
- Second serving: {"yes" if recommendation.get('second_serving_recommended') else "not recommended"}

Keep it practical, honest about the approximate nature of calorie estimates, and encouraging.
Do not give medical advice. Be concise."""

    response = await query_ollama(prompt, model)
    if not response:
        return "Recommendation generated using estimated calorie values. These are approximations — listen to your body and adjust as needed."
    return response.strip()


async def classify_dish(dish_name: str, model: str | None = None) -> dict:
    """Optionally use Ollama to classify an ambiguous dish name."""
    prompt = f"""Classify this dish name for a nutrition tracking app.
Return ONLY a JSON object with:
- "normalized_name": a clean, standardized name for the dish (in Italian if Italian dish, otherwise English)
- "category": one of: primo, secondo, contorno, dessert, extra
- "estimated_calories": estimated calories per standard serving (integer)

Dish: "{dish_name}"

Respond with ONLY the JSON object."""

    response = await query_ollama(prompt, model)
    if not response:
        return {"normalized_name": dish_name.lower().strip(), "category": None, "estimated_calories": None}

    result = _extract_json(response)
    if not result:
        return {"normalized_name": dish_name.lower().strip(), "category": None, "estimated_calories": None}
    return result
