import pytest
from app.services.data_processor import (
    normalize_name,
    slugify,
    map_category,
    classify_claim,
    detect_missing_fields,
    is_duplicate_place,
    process_raw_discovery
)

def test_normalize_name():
    raw = "  Top 10 Places - Galu Devi Temple - TripAdvisor  "
    clean = normalize_name(raw)
    assert "TripAdvisor" not in clean
    assert "Top 10" not in clean
    assert "Galu Devi Temple" in clean

def test_slugify():
    slug = slugify("Veerabhadra Temple Hanging Pillar", "Lepakshi")
    assert "veerabhadra" in slug
    assert "hanging" in slug
    assert " " not in slug

def test_map_category():
    assert map_category("Chaat stall and tea bakery") == "local_food"
    assert map_category("Ancient fort ruins and ASI inscription") == "culture_history"
    assert map_category("Handicraft silk and cotton bazaar") == "markets_shopping"
    assert map_category("Sunset ridge mountain viewpoint") == "nature_scenic"
    assert map_category("Unknown craft village walk") == "local_experiences"

def test_classify_claim():
    folklore_text = "According to ancient folklore and local legends, celestial birds fought here."
    assert classify_claim(folklore_text) == "folklore_oral_tradition"

    documented_text = "Archaeological Survey of India reports document that the granite pillar was built in 1530 AD."
    assert classify_claim(documented_text) == "documented_history"

    personal_text = "We visited early in the morning and bought nice momos from the friendly uncle."
    assert classify_claim(personal_text) == "community_experience"

def test_detect_missing_fields():
    incomplete_place = {
        "short_description": "A quiet viewpoint.",
        "detailed_story": "Very pretty place to look at.",
        "practical_tips": [],
        "source_url": ""
    }
    missing = detect_missing_fields(incomplete_place)
    assert "Exact opening hours unverified" in missing
    assert "Entry fee / ticket details not verified" in missing
    assert "Original web source link pending" in missing

def test_duplicate_detection():
    existing = [
        {"name": "Galu Devi Sunset Trail", "destination": "Naddi, Dharamshala"},
        {"name": "The Hanging Pillar", "destination": "Lepakshi, Andhra Pradesh"}
    ]

    is_dup, matched = is_duplicate_place("Galu Devi Trail", "Dharamshala", existing)
    assert is_dup is True
    assert matched["name"] == "Galu Devi Sunset Trail"

    is_dup2, _ = is_duplicate_place("Taj Mahal", "Agra", existing)
    assert is_dup2 is False
