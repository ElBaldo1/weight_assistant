from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import WeightEntry

router = APIRouter(prefix="/api/weight", tags=["weight"])


@router.get("")
def get_weight_history(limit: int = 30):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM weight_log ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("")
def add_weight_entry(entry: WeightEntry):
    db = get_db()
    try:
        db.execute(
            """INSERT INTO weight_log (date, weight_kg)
               VALUES (?, ?)
               ON CONFLICT(date) DO UPDATE SET weight_kg=excluded.weight_kg""",
            (entry.date, entry.weight_kg),
        )
        # Optionally update profile weight
        db.execute(
            "UPDATE user_profile SET weight_kg = ?, updated_at = datetime('now') WHERE id = 1",
            (entry.weight_kg,),
        )
        db.commit()
        return {"status": "ok", "date": entry.date, "weight_kg": entry.weight_kg}
    finally:
        db.close()


@router.delete("/{entry_id}")
def delete_weight_entry(entry_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM weight_log WHERE id = ?", (entry_id,))
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()
