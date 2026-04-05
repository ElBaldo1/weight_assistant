import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "weight_assistant.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            age INTEGER NOT NULL,
            height_cm REAL NOT NULL,
            weight_kg REAL NOT NULL,
            target_weight_kg REAL NOT NULL,
            sex TEXT NOT NULL CHECK (sex IN ('male', 'female')),
            activity_level TEXT NOT NULL DEFAULT 'moderate'
                CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_menu_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL REFERENCES daily_menu(id) ON DELETE CASCADE,
            category TEXT,
            dish_name TEXT NOT NULL,
            normalized_name TEXT,
            estimated_calories INTEGER,
            is_side INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS dish_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_name TEXT NOT NULL UNIQUE,
            estimated_calories_per_serving INTEGER NOT NULL,
            category TEXT,
            confidence TEXT DEFAULT 'estimated'
                CHECK (confidence IN ('known', 'estimated', 'rough')),
            notes TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            raw_text TEXT,
            workout_type TEXT,
            duration_minutes INTEGER,
            intensity TEXT CHECK (intensity IN ('low', 'medium', 'high')),
            steps INTEGER,
            estimated_calories_burned INTEGER,
            structured_info TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_recommendation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            calorie_target INTEGER,
            activity_calories INTEGER,
            recommended_dishes TEXT,
            bread_recommended INTEGER,
            second_serving_recommended INTEGER,
            lighter_alternative TEXT,
            more_filling_alternative TEXT,
            explanation TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS meal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            dishes TEXT NOT NULL,
            second_serving INTEGER NOT NULL DEFAULT 0,
            bread INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            total_estimated_calories INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # Seed some common dish catalog entries
    seed_dishes = [
        ("pasta al pomodoro", 450, "primo", "estimated"),
        ("pasta al ragu", 520, "primo", "estimated"),
        ("pasta al pesto", 500, "primo", "estimated"),
        ("risotto", 480, "primo", "estimated"),
        ("lasagna", 550, "primo", "estimated"),
        ("minestrone", 200, "primo", "estimated"),
        ("zuppa di legumi", 250, "primo", "estimated"),
        ("pasta e fagioli", 400, "primo", "estimated"),
        ("pollo arrosto", 350, "secondo", "estimated"),
        ("pollo alla griglia", 300, "secondo", "estimated"),
        ("petto di pollo", 280, "secondo", "estimated"),
        ("cotoletta", 450, "secondo", "estimated"),
        ("scaloppina", 320, "secondo", "estimated"),
        ("pesce al forno", 280, "secondo", "estimated"),
        ("merluzzo", 250, "secondo", "estimated"),
        ("tonno", 300, "secondo", "estimated"),
        ("hamburger", 450, "secondo", "estimated"),
        ("polpette", 380, "secondo", "estimated"),
        ("bresaola", 150, "secondo", "estimated"),
        ("insalata mista", 80, "contorno", "estimated"),
        ("insalata verde", 50, "contorno", "estimated"),
        ("verdure grigliate", 120, "contorno", "estimated"),
        ("patate al forno", 250, "contorno", "estimated"),
        ("spinaci", 80, "contorno", "estimated"),
        ("fagiolini", 70, "contorno", "estimated"),
        ("pane", 130, "extra", "estimated"),
        ("frutta", 80, "dessert", "estimated"),
        ("dolce", 350, "dessert", "estimated"),
        ("tiramisù", 400, "dessert", "estimated"),
        ("pizza margherita", 600, "primo", "estimated"),
        ("riso in bianco", 350, "primo", "estimated"),
        ("gnocchi", 450, "primo", "estimated"),
        ("arrosto di vitello", 350, "secondo", "estimated"),
        ("salmone", 350, "secondo", "estimated"),
        ("uova", 200, "secondo", "estimated"),
        ("mozzarella", 250, "secondo", "estimated"),
        ("prosciutto cotto", 200, "secondo", "estimated"),
        ("prosciutto crudo", 220, "secondo", "estimated"),
    ]

    for name, cal, cat, conf in seed_dishes:
        cursor.execute("""
            INSERT OR IGNORE INTO dish_catalog (normalized_name, estimated_calories_per_serving, category, confidence)
            VALUES (?, ?, ?, ?)
        """, (name, cal, cat, conf))

    conn.commit()
    conn.close()
