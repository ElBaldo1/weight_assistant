# Weight Assistant

Local-first personal nutrition and training support app. All data stays on your machine.

## What it does

- **Profile management**: store your age, height, weight, target weight, sex, activity level
- **Weight tracking**: log daily weight, view history and trend
- **Menu ingestion**: fetch the daily menu from a local API or enter it manually; dishes are matched to a calorie catalog (~35 pre-seeded Italian dishes)
- **Workout logging**: describe your workout in free text; Ollama interprets it into a structured type (running, cycling, etc.); calories are estimated deterministically via MET formulas
- **Daily recommendation**: based on your profile, weight goal, activity, and today's menu, the app suggests which dishes to eat, whether to add bread or take a second serving, plus a lighter and a more filling alternative
- **Meal logging**: record what you actually ate each day
- **Dashboard**: single-page overview of today's profile, menu, activity, recommendation, and meals

All calorie calculations are deterministic (Mifflin-St Jeor BMR, MET-based workout calories). Ollama is used only for text interpretation and generating natural language explanations.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Ollama](https://ollama.ai/) (optional, for AI-assisted workout interpretation and explanations)

## Quick Start

```bash
# Install dependencies
uv sync

# Start the app
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Open in browser
open http://127.0.0.1:8000
```

## Ollama Setup (Optional)

Ollama is used for interpreting workout descriptions and generating recommendation explanations. The app works without it using sensible fallbacks.

```bash
# Install Ollama from https://ollama.ai/
# Then pull a model (the app defaults to qwen3.5:9b):
ollama pull qwen3.5:9b

# Ollama runs on http://localhost:11434 by default
```

To use a different model, change `DEFAULT_MODEL` in `backend/services/ollama_service.py`.

The app auto-detects Ollama availability and shows status in the header.

## Menu API

The app fetches the daily menu from `http://10.0.1.4:3000/menuAPI`. If the menu API is unavailable, you can add menu items manually through the Menu tab.

## Project Structure

```
weight_assistant/
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── database.py                      # SQLite schema and initialization
│   ├── models.py                        # Pydantic models
│   ├── routers/
│   │   ├── profile.py                   # Profile CRUD
│   │   ├── weight.py                    # Weight log CRUD
│   │   ├── menu.py                      # Menu fetch / store
│   │   ├── workout.py                   # Workout logging with Ollama
│   │   ├── meal_log.py                  # Meal logging
│   │   ├── recommendation.py            # Daily recommendation
│   │   └── dish_catalog.py              # Dish catalog management
│   └── services/
│       ├── calorie_calculator.py        # BMR, TDEE, workout calories (deterministic)
│       ├── menu_service.py              # Menu fetching and parsing
│       ├── recommendation_engine.py     # Meal recommendation logic (deterministic)
│       └── ollama_service.py            # Local Ollama integration
├── frontend/
│   ├── index.html                       # Single-page app
│   ├── style.css                        # Styles
│   └── app.js                           # Frontend logic
├── data/                                # SQLite database (auto-created)
├── pyproject.toml
└── README.md
```

## Database

SQLite database is created automatically at `data/weight_assistant.db` on first run. Tables:

- `user_profile` - single-row profile (age, height, weight, target, sex, activity level)
- `weight_log` - weight entries by date
- `daily_menu` - raw menu data fetched from API
- `daily_menu_item` - parsed menu items with calorie estimates
- `dish_catalog` - known dishes with estimated calories (pre-seeded with ~35 common items)
- `daily_activity` - workout/activity entries
- `daily_recommendation` - generated recommendations
- `meal_log` - what was actually eaten

## Design Decisions

### LLM vs Deterministic Logic

All numerical calculations are deterministic:
- **BMR**: Mifflin-St Jeor equation
- **TDEE**: BMR × activity multiplier
- **Daily target**: TDEE ± deficit/surplus based on weight goal
- **Workout calories**: MET-based formula (MET × weight × duration)
- **Step calories**: 0.04 kcal per step per 70kg body weight
- **Recommendation**: budget-based meal selection from menu items

Ollama is only used for:
- Interpreting free-text workout descriptions into structured workout types
- Generating natural language recommendation explanations
- Optionally classifying unknown dish names

### Calorie Estimates

All calorie values are estimates. The app uses:
- A seeded catalog of ~35 common dishes
- Partial name matching for menu items not in the catalog
- Conservative deficit/surplus calculations (max 500 kcal/day deficit for weight loss)
- Safe minimums (1500 kcal/day for males, 1200 for females)

## Daily Workflow

1. Open the app at http://127.0.0.1:8000
2. Set up your profile (first time only)
3. Log your weight
4. Fetch today's menu (or it's fetched automatically)
5. Log your workout/activity
6. Check the recommendation on the dashboard
7. Log what you actually ate
