import json
from fastapi import APIRouter
from datetime import date

from backend.database import get_db
from backend.services.recommendation_engine import generate_recommendation
from backend.services.ollama_service import generate_recommendation_explanation
from backend.services.menu_service import get_today_menu

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


@router.get("")
async def get_recommendation(target_date: str | None = None, model: str | None = None):
    """Generate today's recommendation based on profile, menu, and activity."""
    date_str = target_date or date.today().isoformat()
    db = get_db()

    try:
        # Get profile
        profile_row = db.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        if not profile_row:
            return {
                "status": "error",
                "message": "No profile found. Please set up your profile first.",
            }
        profile = dict(profile_row)

        # Get today's menu
        menu = get_today_menu(date_str)
        if not menu or not menu.get("items"):
            return {
                "status": "error",
                "message": f"No menu found for {date_str}. Please fetch the menu first.",
            }

        # Get today's activities
        activity_rows = db.execute(
            "SELECT * FROM daily_activity WHERE date = ?", (date_str,)
        ).fetchall()
        activities = [dict(r) for r in activity_rows]

        # Generate deterministic recommendation
        rec = generate_recommendation(
            profile=profile,
            menu_items=menu["items"],
            activities=activities,
        )

        # Try to generate explanation via Ollama
        try:
            explanation = await generate_recommendation_explanation(
                recommendation=rec,
                profile=profile,
                model=model,
            )
            rec["explanation"] = explanation
        except Exception:
            rec["explanation"] = (
                "Recommendation based on estimated calorie values. "
                "These are approximations — listen to your body and adjust as needed."
            )

        # Store recommendation
        db.execute(
            """INSERT INTO daily_recommendation
               (date, calorie_target, activity_calories, recommended_dishes,
                bread_recommended, second_serving_recommended,
                lighter_alternative, more_filling_alternative, explanation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date_str,
                rec["calorie_target"],
                rec["activity_calories"],
                json.dumps(rec["recommended_dishes"], ensure_ascii=False),
                1 if rec["bread_recommended"] else 0,
                1 if rec["second_serving_recommended"] else 0,
                json.dumps(rec["lighter_alternative"], ensure_ascii=False),
                json.dumps(rec["more_filling_alternative"], ensure_ascii=False),
                rec["explanation"],
            ),
        )
        db.commit()

        return {"status": "ok", "date": date_str, **rec}

    finally:
        db.close()


@router.get("/history")
def get_recommendation_history(limit: int = 14):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM daily_recommendation ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["recommended_dishes"] = json.loads(d["recommended_dishes"])
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                d["lighter_alternative"] = json.loads(d["lighter_alternative"])
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                d["more_filling_alternative"] = json.loads(d["more_filling_alternative"])
            except (json.JSONDecodeError, TypeError):
                pass
            results.append(d)
        return results
    finally:
        db.close()
