from fastapi import APIRouter
from backend.database import get_db
from backend.models import DishCatalogEntry
from backend.services.ollama_service import classify_dish

router = APIRouter(prefix="/api/dishes", tags=["dishes"])


@router.get("")
def get_all_dishes(search: str | None = None):
    db = get_db()
    try:
        if search:
            rows = db.execute(
                "SELECT * FROM dish_catalog WHERE normalized_name LIKE ? ORDER BY normalized_name",
                (f"%{search.lower()}%",),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM dish_catalog ORDER BY category, normalized_name"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("")
def add_dish(dish: DishCatalogEntry):
    db = get_db()
    try:
        db.execute(
            """INSERT INTO dish_catalog (normalized_name, estimated_calories_per_serving, category, confidence, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(normalized_name) DO UPDATE SET
                 estimated_calories_per_serving=excluded.estimated_calories_per_serving,
                 category=excluded.category,
                 confidence=excluded.confidence,
                 notes=excluded.notes,
                 updated_at=datetime('now')""",
            (dish.normalized_name.lower().strip(), dish.estimated_calories_per_serving,
             dish.category, dish.confidence, dish.notes),
        )
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@router.post("/classify")
async def classify_dish_name(dish_name: str, model: str | None = None):
    """Use Ollama to classify an unknown dish."""
    result = await classify_dish(dish_name, model)
    return result


@router.delete("/{dish_id}")
def delete_dish(dish_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM dish_catalog WHERE id = ?", (dish_id,))
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()
