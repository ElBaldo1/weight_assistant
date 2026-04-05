from fastapi import APIRouter
from datetime import date

from backend.services.menu_service import (
    fetch_menu_from_api,
    parse_menu_items,
    store_menu,
    get_today_menu,
)

router = APIRouter(prefix="/api/menu", tags=["menu"])


@router.get("/fetch")
async def fetch_and_store_menu(target_date: str | None = None):
    """Fetch menu from external API and store it."""
    date_str = target_date or date.today().isoformat()

    raw_menu = await fetch_menu_from_api()
    if raw_menu is None:
        return {
            "status": "error",
            "message": "Could not fetch menu from API. The menu service may be unavailable.",
        }

    items = parse_menu_items(raw_menu)
    if not items:
        return {
            "status": "warning",
            "message": "Menu fetched but no items could be parsed.",
            "raw": raw_menu,
        }

    menu_id = store_menu(date_str, raw_menu, items)
    return {
        "status": "ok",
        "menu_id": menu_id,
        "date": date_str,
        "items_count": len(items),
        "items": items,
    }


@router.get("/today")
def get_menu_today(target_date: str | None = None):
    """Get the stored menu for today or a given date."""
    date_str = target_date or date.today().isoformat()
    menu = get_today_menu(date_str)
    if not menu:
        return {"status": "no_menu", "date": date_str, "message": "No menu stored for this date. Try fetching first."}
    return {"status": "ok", **menu}


@router.post("/manual")
def add_menu_manually(target_date: str | None = None, items: list[dict] = []):
    """Manually add menu items for a date."""
    date_str = target_date or date.today().isoformat()
    if not items:
        return {"status": "error", "message": "No items provided."}

    menu_id = store_menu(date_str, {"manual": True, "items": items}, items)
    return {"status": "ok", "menu_id": menu_id, "date": date_str, "items_count": len(items)}
