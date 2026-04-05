"""Service for fetching and processing the daily menu from the external API."""

import httpx
import json
import logging
from datetime import date

from backend.database import get_db

logger = logging.getLogger(__name__)

MENU_API_URL = "http://10.0.1.4:3000/menuAPI"


async def fetch_menu_from_api() -> dict | None:
    """Fetch today's menu from the external local API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(MENU_API_URL)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Menu API returned status {resp.status_code}")
                return None
    except Exception as e:
        logger.warning(f"Failed to fetch menu: {e}")
        return None


def normalize_dish_name(name: str) -> str:
    """Basic normalization of dish names."""
    return name.strip().lower()


def lookup_dish_calories(normalized_name: str) -> tuple[int | None, str]:
    """
    Look up estimated calories for a dish from the catalog.
    Returns (calories, confidence) or (None, 'unknown').
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT estimated_calories_per_serving, confidence FROM dish_catalog WHERE normalized_name = ?",
            (normalized_name,),
        ).fetchone()
        if row:
            return row["estimated_calories_per_serving"], row["confidence"]

        # Try partial match
        row = db.execute(
            "SELECT estimated_calories_per_serving, confidence FROM dish_catalog WHERE ? LIKE '%' || normalized_name || '%' OR normalized_name LIKE '%' || ? || '%' LIMIT 1",
            (normalized_name, normalized_name),
        ).fetchone()
        if row:
            return row["estimated_calories_per_serving"], row["confidence"]

        return None, "unknown"
    finally:
        db.close()


def store_menu(date_str: str, raw_json: dict, items: list[dict]) -> int:
    """Store a fetched menu and its items in the database."""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO daily_menu (date, raw_json) VALUES (?, ?)",
            (date_str, json.dumps(raw_json, ensure_ascii=False)),
        )
        menu_id = cursor.lastrowid

        for item in items:
            normalized = normalize_dish_name(item.get("name", ""))
            cal, _ = lookup_dish_calories(normalized)
            db.execute(
                """INSERT INTO daily_menu_item (menu_id, category, dish_name, normalized_name, estimated_calories, is_side)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    menu_id,
                    item.get("category"),
                    item.get("name", ""),
                    normalized,
                    cal,
                    1 if item.get("is_side") else 0,
                ),
            )

        db.commit()
        return menu_id
    finally:
        db.close()


def get_today_menu(date_str: str | None = None) -> dict | None:
    """Get the stored menu for today (or a given date)."""
    if date_str is None:
        date_str = date.today().isoformat()

    db = get_db()
    try:
        menu_row = db.execute(
            "SELECT * FROM daily_menu WHERE date = ? ORDER BY fetched_at DESC LIMIT 1",
            (date_str,),
        ).fetchone()

        if not menu_row:
            return None

        items = db.execute(
            "SELECT * FROM daily_menu_item WHERE menu_id = ?",
            (menu_row["id"],),
        ).fetchall()

        return {
            "id": menu_row["id"],
            "date": menu_row["date"],
            "raw_json": json.loads(menu_row["raw_json"]),
            "fetched_at": menu_row["fetched_at"],
            "items": [dict(item) for item in items],
        }
    finally:
        db.close()


def parse_menu_items(raw_menu: dict) -> list[dict]:
    """
    Parse the raw API response into a list of menu items.
    Adapts to various possible formats from the API.
    """
    items = []

    if isinstance(raw_menu, list):
        for entry in raw_menu:
            if isinstance(entry, str):
                items.append({"name": entry, "category": None})
            elif isinstance(entry, dict):
                items.append({
                    "name": entry.get("name") or entry.get("dish") or entry.get("piatto") or str(entry),
                    "category": entry.get("category") or entry.get("categoria") or entry.get("type"),
                    "is_side": entry.get("is_side", False),
                })
    elif isinstance(raw_menu, dict):
        # Could be categorized: {"primi": [...], "secondi": [...], ...}
        for key, value in raw_menu.items():
            if isinstance(value, list):
                for dish in value:
                    if isinstance(dish, str):
                        items.append({"name": dish, "category": key})
                    elif isinstance(dish, dict):
                        items.append({
                            "name": dish.get("name") or dish.get("dish") or dish.get("piatto") or str(dish),
                            "category": key,
                            "is_side": dish.get("is_side", False),
                        })
            elif isinstance(value, str):
                items.append({"name": value, "category": key})

    return items
