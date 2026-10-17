import pytest
from app.services.recommendation_engine import rank_places

def test_rank_places_query_relevance():
    places = [
        {
            "name": "Random Scenic Valley",
            "destination": "Shimla",
            "category": "nature_scenic",
            "short_description": "Pine trees and hills.",
            "detailed_story": "A long story about pine trees.",
            "practical_tips": ["Wear boots"],
            "budget_tier": "free",
            "source_type": "stored_archive"
        },
        {
            "name": "Sarojini Nagar Export Lane",
            "destination": "Sarojini Nagar, Delhi",
            "category": "markets_shopping",
            "short_description": "Export surplus shopping.",
            "detailed_story": "A detailed history of factory surplus garments in Sarojini.",
            "practical_tips": ["Carry cash", "Visit Tuesday morning"],
            "budget_tier": "budget",
            "source_type": "stored_archive"
        }
    ]

    # Searching for "Sarojini" should rank Sarojini first
    ranked = rank_places(places, query="Sarojini", category_filter="markets_shopping")
    assert ranked[0]["name"] == "Sarojini Nagar Export Lane"
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]
    assert "Sarojini" in ranked[0]["score_breakdown"]["explanation"]

def test_rank_places_completeness_bonus():
    sparse_place = {
        "name": "Spot A",
        "destination": "Goa",
        "category": "nature_scenic",
        "short_description": "A place.",
        "detailed_story": "Small text.",
        "practical_tips": [],
        "budget_tier": "free",
        "source_type": "stored_archive"
    }
    rich_place = {
        "name": "Spot B",
        "destination": "Goa",
        "category": "nature_scenic",
        "short_description": "A well documented quiet cove with historic coconut palms.",
        "detailed_story": "Extensive cultural and geographical breakdown of this seaside gem.",
        "practical_tips": ["Visit at low tide", "Bring reef shoes", "Respect local fishing nets"],
        "budget_tier": "free",
        "source_url": "https://example.com/source",
        "source_type": "stored_archive"
    }

    ranked = rank_places([sparse_place, rich_place], query="Goa")
    assert ranked[0]["name"] == "Spot B"
    assert ranked[0]["score_breakdown"]["information_completeness"] > ranked[1]["score_breakdown"]["information_completeness"]
