from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut | None)
def get_profile():
    db = get_db()
    try:
        row = db.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        db.close()


@router.put("", response_model=ProfileOut)
def save_profile(profile: ProfileIn):
    db = get_db()
    try:
        db.execute(
            """INSERT INTO user_profile (id, age, height_cm, weight_kg, target_weight_kg, sex, activity_level, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(id) DO UPDATE SET
                 age=excluded.age,
                 height_cm=excluded.height_cm,
                 weight_kg=excluded.weight_kg,
                 target_weight_kg=excluded.target_weight_kg,
                 sex=excluded.sex,
                 activity_level=excluded.activity_level,
                 updated_at=datetime('now')""",
            (profile.age, profile.height_cm, profile.weight_kg,
             profile.target_weight_kg, profile.sex, profile.activity_level),
        )
        db.commit()
        row = db.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        return dict(row)
    finally:
        db.close()
