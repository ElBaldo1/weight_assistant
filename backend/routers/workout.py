import json
from fastapi import APIRouter
from backend.database import get_db
from backend.models import WorkoutIn, WorkoutOut
from backend.services.calorie_calculator import estimate_workout_calories, estimate_steps_calories
from backend.services.ollama_service import interpret_workout

router = APIRouter(prefix="/api/workout", tags=["workout"])


@router.get("")
def get_workouts(target_date: str | None = None, limit: int = 30):
    db = get_db()
    try:
        if target_date:
            rows = db.execute(
                "SELECT * FROM daily_activity WHERE date = ? ORDER BY created_at DESC", (target_date,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM daily_activity ORDER BY date DESC, created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("")
async def add_workout(workout: WorkoutIn):
    db = get_db()
    try:
        # Get profile for weight-based calorie estimation
        profile = db.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        weight_kg = profile["weight_kg"] if profile else 75.0

        # Use Ollama to interpret workout text
        structured = {"workout_type": "general", "summary": workout.raw_text}
        if workout.raw_text.strip():
            structured = await interpret_workout(workout.raw_text)

        workout_type = structured.get("workout_type", "general")

        # Deterministic calorie estimation
        calories = 0
        if workout.duration_minutes and workout.duration_minutes > 0:
            calories = estimate_workout_calories(
                workout_type=workout_type,
                duration_minutes=workout.duration_minutes,
                weight_kg=weight_kg,
                intensity=workout.intensity,
            )

        if workout.steps and workout.steps > 0:
            calories += estimate_steps_calories(workout.steps, weight_kg)

        cursor = db.execute(
            """INSERT INTO daily_activity (date, raw_text, workout_type, duration_minutes, intensity, steps, estimated_calories_burned, structured_info)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                workout.date,
                workout.raw_text,
                workout_type,
                workout.duration_minutes,
                workout.intensity,
                workout.steps,
                calories,
                json.dumps(structured, ensure_ascii=False),
            ),
        )
        db.commit()

        return {
            "status": "ok",
            "id": cursor.lastrowid,
            "workout_type": workout_type,
            "estimated_calories_burned": calories,
            "structured_info": structured,
        }
    finally:
        db.close()


@router.delete("/{workout_id}")
def delete_workout(workout_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM daily_activity WHERE id = ?", (workout_id,))
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()
