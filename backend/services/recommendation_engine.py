"""
Deterministic recommendation engine.
All logic is implemented in code, not delegated to the LLM.
The LLM is only used for generating the natural language explanation.
"""

from backend.services.calorie_calculator import (
    calculate_daily_target,
    estimate_workout_calories,
    estimate_steps_calories,
)
from backend.services.menu_service import lookup_dish_calories, normalize_dish_name

BREAD_CALORIES = 130


def generate_recommendation(
    profile: dict,
    menu_items: list[dict],
    activities: list[dict],
) -> dict:
    """
    Generate a meal recommendation based on profile, menu, and daily activity.
    Returns a structured recommendation dict.
    """
    # Calculate calorie target
    target_info = calculate_daily_target(
        weight_kg=profile["weight_kg"],
        height_cm=profile["height_cm"],
        age=profile["age"],
        sex=profile["sex"],
        target_weight_kg=profile["target_weight_kg"],
        activity_level=profile.get("activity_level", "moderate"),
    )

    # Calculate activity calories
    activity_calories = 0
    for act in activities:
        if act.get("estimated_calories_burned"):
            activity_calories += act["estimated_calories_burned"]
        elif act.get("duration_minutes") and act.get("duration_minutes") > 0:
            activity_calories += estimate_workout_calories(
                workout_type=act.get("workout_type", "general"),
                duration_minutes=act["duration_minutes"],
                weight_kg=profile["weight_kg"],
                intensity=act.get("intensity"),
            )
        if act.get("steps") and act["steps"] > 0:
            activity_calories += estimate_steps_calories(act["steps"], profile["weight_kg"])

    # Adjusted calorie budget for today
    calorie_budget = target_info["daily_target"] + activity_calories

    # Estimate calories for each menu item
    scored_items = []
    for item in menu_items:
        normalized = normalize_dish_name(item.get("dish_name") or item.get("name", ""))
        cal = item.get("estimated_calories")
        confidence = "estimated"
        if cal is None:
            cal, confidence = lookup_dish_calories(normalized)
        scored_items.append({
            "name": item.get("dish_name") or item.get("name", ""),
            "normalized_name": normalized,
            "category": item.get("category", ""),
            "estimated_calories": cal,
            "confidence": confidence,
        })

    # Split by category
    primi = [i for i in scored_items if _is_category(i["category"], "primo")]
    secondi = [i for i in scored_items if _is_category(i["category"], "secondo")]
    contorni = [i for i in scored_items if _is_category(i["category"], "contorno")]
    desserts = [i for i in scored_items if _is_category(i["category"], "dessert")]
    other = [i for i in scored_items if not any(
        _is_category(i["category"], c) for c in ("primo", "secondo", "contorno", "dessert")
    )]

    # Build a standard meal: primo + secondo + contorno
    # Target roughly: 40% primo, 35% secondo, 15% contorno, 10% bread/extra
    meal_budget = calorie_budget * 0.40  # Assuming lunch is ~40% of daily calories

    recommended = _pick_meal(primi, secondi, contorni, meal_budget)
    recommended_cal = sum(d["estimated_calories"] or 0 for d in recommended["dishes"])

    # Bread decision
    remaining_after_meal = meal_budget - recommended_cal
    bread_recommended = remaining_after_meal > BREAD_CALORIES
    if bread_recommended:
        recommended_cal += BREAD_CALORIES

    # Second serving decision
    remaining_after_bread = meal_budget - recommended_cal
    second_serving_recommended = remaining_after_bread > 200 and target_info["goal"] != "lose"

    # Lighter alternative: skip the highest calorie item and pick the lowest
    lighter = _pick_meal(primi, secondi, contorni, meal_budget * 0.75)
    lighter_cal = sum(d["estimated_calories"] or 0 for d in lighter["dishes"])

    # More filling alternative: include bread + potentially second serving
    filling = _pick_meal(primi, secondi, contorni, meal_budget * 1.2)
    filling_cal = sum(d["estimated_calories"] or 0 for d in filling["dishes"])

    return {
        "calorie_target": target_info["daily_target"],
        "bmr": target_info["bmr"],
        "tdee": target_info["tdee"],
        "goal": target_info["goal"],
        "activity_calories": activity_calories,
        "meal_calorie_budget": round(meal_budget),
        "recommended_dishes": [d["name"] for d in recommended["dishes"]],
        "recommended_calories": recommended_cal,
        "bread_recommended": bread_recommended,
        "second_serving_recommended": second_serving_recommended,
        "lighter_alternative": {
            "dishes": [d["name"] for d in lighter["dishes"]],
            "estimated_calories": lighter_cal,
        },
        "more_filling_alternative": {
            "dishes": [d["name"] for d in filling["dishes"]],
            "estimated_calories": filling_cal,
            "bread": True,
            "second_serving": target_info["goal"] == "gain",
        },
        "all_items_scored": scored_items,
        "explanation": None,  # Will be filled by Ollama if available
    }


def _is_category(item_cat: str | None, target: str) -> bool:
    if not item_cat:
        return False
    cat = item_cat.lower().strip()
    mappings = {
        "primo": ["primo", "primi", "first", "pasta", "soup", "zuppa", "risotto"],
        "secondo": ["secondo", "secondi", "second", "main", "meat", "fish", "carne", "pesce"],
        "contorno": ["contorno", "contorni", "side", "vegetable", "verdura", "insalata"],
        "dessert": ["dessert", "dolce", "dolci", "fruit", "frutta", "sweet"],
    }
    return cat in mappings.get(target, [])


def _pick_meal(
    primi: list[dict],
    secondi: list[dict],
    contorni: list[dict],
    budget: float,
) -> dict:
    """Pick one primo, one secondo, one contorno that best fits the budget."""
    dishes = []

    # Sort by calories (pick lower cal items for tighter budgets)
    def cal_key(item):
        return item.get("estimated_calories") or 400

    # Pick a primo (allocate ~45% of meal budget to primo)
    primo_budget = budget * 0.45
    primo = _pick_closest(primi, primo_budget)
    if primo:
        dishes.append(primo)

    # Pick a secondo (allocate ~40% to secondo)
    secondo_budget = budget * 0.40
    secondo = _pick_closest(secondi, secondo_budget)
    if secondo:
        dishes.append(secondo)

    # Pick a contorno (allocate remaining ~15%)
    contorno_budget = budget * 0.15
    contorno = _pick_closest(contorni, contorno_budget)
    if contorno:
        dishes.append(contorno)

    return {"dishes": dishes}


def _pick_closest(items: list[dict], budget: float) -> dict | None:
    """Pick the item whose calories are closest to the budget without going too far over."""
    if not items:
        return None

    scored = []
    for item in items:
        cal = item.get("estimated_calories") or 400
        # Prefer items slightly under budget
        diff = cal - budget
        # Penalize going over budget more than going under
        score = abs(diff) if diff <= 0 else diff * 1.5
        scored.append((score, item))

    scored.sort(key=lambda x: x[0])
    return scored[0][1]
