"""
Deterministic calorie calculation logic.
Uses Mifflin-St Jeor equation for BMR and standard activity multipliers.
All calorie estimates are approximate and clearly communicated as such.
"""


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor BMR equation."""
    if sex == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Total Daily Energy Expenditure = BMR * activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return bmr * multiplier


def calculate_daily_target(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    target_weight_kg: float,
    activity_level: str,
) -> dict:
    """
    Calculate daily calorie target for gradual weight change.
    Uses a conservative 500 kcal/day deficit for weight loss
    or 300 kcal/day surplus for weight gain.
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    tdee = calculate_tdee(bmr, activity_level)

    diff = weight_kg - target_weight_kg

    if diff > 1:
        # Weight loss: deficit of 300-500 kcal depending on how far from target
        deficit = min(500, max(300, diff * 50))
        target = tdee - deficit
        goal = "lose"
    elif diff < -1:
        # Weight gain: surplus of 200-300 kcal
        surplus = min(300, max(200, abs(diff) * 40))
        target = tdee + surplus
        goal = "gain"
    else:
        target = tdee
        goal = "maintain"

    # Never go below a safe minimum
    min_calories = 1200 if sex == "female" else 1500
    target = max(target, min_calories)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "daily_target": round(target),
        "goal": goal,
        "deficit_or_surplus": round(abs(tdee - target)),
    }


# MET values for common workout types.
# These are conservative estimates for typical recreational/amateur intensity.
# Source: Compendium of Physical Activities.
MET_VALUES = {
    "running": 8.0,
    "jogging": 7.0,
    "cycling": 6.8,
    "swimming": 7.0,
    "walking": 3.5,
    "hiking": 5.5,
    "weight_training": 3.5,
    "strength": 3.5,
    "yoga": 2.5,
    "pilates": 3.0,
    "stretching": 2.3,
    "hiit": 8.0,
    "crossfit": 8.0,
    "elliptical": 5.0,
    "rowing": 6.0,
    "dancing": 4.5,
    "boxing": 7.5,
    "martial_arts": 7.0,
    "climbing": 7.0,
    "tennis": 6.0,
    "soccer": 6.0,
    "basketball": 6.0,
    "general": 4.0,
    "other": 4.0,
}


def estimate_workout_calories(
    workout_type: str,
    duration_minutes: int,
    weight_kg: float,
    intensity: str | None = None,
) -> int:
    """
    Estimate NET calories burned using MET formula:
    Net Calories = (MET - 1) * weight_kg * duration_hours

    We subtract 1 MET (resting metabolic rate) because TDEE already
    accounts for resting calories. This avoids double-counting.

    Intensity modifies the MET value:
    - low: 0.85x
    - medium: 1.0x
    - high: 1.2x
    """
    workout_type_lower = (workout_type or "general").lower().strip()
    met = MET_VALUES.get(workout_type_lower, 4.0)

    intensity_multipliers = {"low": 0.85, "medium": 1.0, "high": 1.2}
    if intensity:
        met *= intensity_multipliers.get(intensity, 1.0)

    # Subtract 1 MET for resting (already in TDEE)
    net_met = max(met - 1.0, 0.5)
    duration_hours = duration_minutes / 60.0
    calories = net_met * weight_kg * duration_hours
    return round(calories)


def estimate_steps_calories(steps: int, weight_kg: float) -> int:
    """
    Rough estimate: ~0.04 kcal per step for a 70kg person, scaled by weight.
    10,000 steps ~ 300-400 kcal for an average person.
    """
    base_cal_per_step = 0.035
    return round(steps * base_cal_per_step * (weight_kg / 70.0))
