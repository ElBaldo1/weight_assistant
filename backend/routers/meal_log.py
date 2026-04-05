from fastapi import APIRouter
from backend.database import get_db
from backend.models import MealLogIn
from backend.services.menu_service import normalize_dish_name, lookup_dish_calories

router = APIRouter(prefix="/api/meals", tags=["meals"])


@router.get("")
def get_meal_logs(target_date: str | None = None, limit: int = 30):
    db = get_db()
    try:
        if target_date:
            rows = db.execute(
                "SELECT * FROM meal_log WHERE date = ? ORDER BY created_at DESC", (target_date,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM meal_log ORDER BY date DESC, created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("")
def log_meal(meal: MealLogIn):
    db = get_db()
    try:
        # Estimate total calories from listed dishes
        total_cal = 0
        dish_names = [d.strip() for d in meal.dishes.split(",") if d.strip()]
        for dish_name in dish_names:
            normalized = normalize_dish_name(dish_name)
            cal, _ = lookup_dish_calories(normalized)
            if cal:
                total_cal += cal

        if meal.bread:
            total_cal += 130

        if meal.second_serving:
            # Assume the most caloric dish is taken again (rough estimate)
            max_dish_cal = 0
            for dish_name in dish_names:
                normalized = normalize_dish_name(dish_name)
                cal, _ = lookup_dish_calories(normalized)
                if cal and cal > max_dish_cal:
                    max_dish_cal = cal
            total_cal += max_dish_cal

        cursor = db.execute(
            """INSERT INTO meal_log (date, dishes, second_serving, bread, notes, total_estimated_calories)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (meal.date, meal.dishes, 1 if meal.second_serving else 0,
             1 if meal.bread else 0, meal.notes, total_cal if total_cal > 0 else None),
        )
        db.commit()

        return {
            "status": "ok",
            "id": cursor.lastrowid,
            "total_estimated_calories": total_cal if total_cal > 0 else None,
        }
    finally:
        db.close()


@router.delete("/{meal_id}")
def delete_meal_log(meal_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM meal_log WHERE id = ?", (meal_id,))
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()
