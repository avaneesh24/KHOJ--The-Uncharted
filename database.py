import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings

# Resolve SQLite database file location consistently
if settings.DATABASE_URL.startswith("sqlite:///"):
    raw_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if os.path.isabs(raw_path):
        DB_FILE = raw_path
    else:
        # Resolve relative to the backend directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        DB_FILE = os.path.normpath(os.path.join(base_dir, raw_path))
else:
    DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "khoj.db"))

def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Places table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        destination TEXT NOT NULL,
        short_description TEXT NOT NULL,
        detailed_story TEXT NOT NULL,
        claim_type TEXT NOT NULL DEFAULT 'community_experience',
        practical_tips TEXT NOT NULL DEFAULT '[]',
        budget_tier TEXT NOT NULL DEFAULT 'moderate',
        source_url TEXT NOT NULL DEFAULT '',
        source_title TEXT NOT NULL DEFAULT '',
        source_type TEXT NOT NULL DEFAULT 'stored_archive',
        retrieved_at TEXT NOT NULL,
        freshness_indicator TEXT NOT NULL DEFAULT 'recently_verified',
        missing_fields_flag TEXT NOT NULL DEFAULT '[]',
        upvotes INTEGER NOT NULL DEFAULT 0,
        is_approved INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # Community contributions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS community_contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_name TEXT NOT NULL,
        destination TEXT NOT NULL,
        category TEXT NOT NULL,
        contribution_type TEXT NOT NULL,
        details TEXT NOT NULL,
        practical_tips TEXT NOT NULL DEFAULT '',
        source_reference TEXT NOT NULL DEFAULT '',
        contributor_name TEXT NOT NULL DEFAULT 'Anonymous Explorer',
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL
    )
    """)

    # Feedback and inaccuracy reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER,
        place_name TEXT NOT NULL,
        report_type TEXT NOT NULL,
        notes TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Indexes for fast search
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_destination ON places(destination)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_category ON places(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_name ON places(name)")

    conn.commit()
    sync_community_contributions_to_places(conn)
    conn.close()

def sync_community_contributions_to_places(conn):
    """
    Non-destructively promotes community_contributions of type 'new_place'
    into the searchable places table if not already present.
    """
    from app.services.data_processor import (
        is_duplicate_place,
        normalize_name,
        slugify,
        map_category
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places")
    existing_places = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM community_contributions WHERE contribution_type = 'new_place' ORDER BY id ASC")
    contribs = cursor.fetchall()

    for c in contribs:
        is_dup, _ = is_duplicate_place(c["place_name"], c["destination"], existing_places)
        if not is_dup:
            clean_name = normalize_name(c["place_name"])
            base_slug = slugify(clean_name, c["destination"])
            unique_slug = base_slug
            suffix = 1
            while True:
                cursor.execute("SELECT id FROM places WHERE slug = ?", (unique_slug,))
                if not cursor.fetchone():
                    break
                suffix += 1
                unique_slug = f"{base_slug}-{suffix}"

            short_desc = c["details"].strip()
            if len(short_desc) > 150:
                short_desc = short_desc[:146].rsplit(" ", 1)[0] + "..."

            mapped_cat = map_category(c["category"], f"{clean_name} {c['details']}")
            tips_list = [c["practical_tips"].strip()] if c["practical_tips"] and c["practical_tips"].strip() else []

            cursor.execute("""
            INSERT INTO places (
                name, slug, category, destination, short_description, detailed_story,
                claim_type, practical_tips, budget_tier, source_url, source_title,
                source_type, retrieved_at, freshness_indicator, missing_fields_flag,
                upvotes, is_approved, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clean_name,
                unique_slug,
                mapped_cat,
                c["destination"].strip(),
                short_desc,
                c["details"].strip(),
                "community_experience",
                json.dumps(tips_list),
                "moderate",
                c["source_reference"] or "",
                f"Community by {c['contributor_name'] or 'Anonymous Explorer'}",
                "community_verified",
                c["created_at"],
                "recently_verified",
                json.dumps([]),
                1,
                1,
                c["created_at"]
            ))
            existing_places.append({"name": clean_name, "destination": c["destination"]})

    conn.commit()

def check_db_health() -> Dict[str, Any]:
    """Check database status and record count."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM places")
        places_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM community_contributions")
        contrib_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM feedback_reports")
        feedback_count = cursor.fetchone()["count"]
        conn.close()
        return {
            "status": "healthy",
            "engine": "sqlite" if settings.is_sqlite else "postgresql",
            "database_file": DB_FILE,
            "places_count": places_count,
            "contributions_count": contrib_count,
            "feedback_count": feedback_count
        }
    except Exception as e:
        return {
            "status": "error",
            "engine": "sqlite",
            "error": str(e)
        }
