import sys
import os
import unittest

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.data_processor import (
    normalize_name,
    slugify,
    map_category,
    classify_claim,
    detect_missing_fields,
    is_duplicate_place
)
from app.services.recommendation_engine import rank_places
from app.database import init_db
from seed_data import seed_database
from app.routers.discovery import search_discoveries
from app.schemas import ContributionCreate, FeedbackCreate

class TestDataProcessor(unittest.TestCase):
    def test_normalize_name(self):
        raw = "  Top 10 Places - Galu Devi Temple - TripAdvisor  "
        clean = normalize_name(raw)
        self.assertNotIn("TripAdvisor", clean)
        self.assertNotIn("Top 10", clean)
        self.assertIn("Galu Devi Temple", clean)

    def test_slugify(self):
        slug = slugify("Veerabhadra Temple Hanging Pillar", "Lepakshi")
        self.assertIn("veerabhadra", slug)
        self.assertIn("hanging", slug)
        self.assertNotIn(" ", slug)

    def test_map_category(self):
        self.assertEqual(map_category("Chaat stall and tea bakery"), "local_food")
        self.assertEqual(map_category("Ancient fort ruins and ASI inscription"), "culture_history")
        self.assertEqual(map_category("Handicraft silk and cotton bazaar"), "markets_shopping")
        self.assertEqual(map_category("Sunset ridge mountain viewpoint"), "nature_scenic")
        self.assertEqual(map_category("Unknown craft village walk"), "local_experiences")

    def test_classify_claim(self):
        folklore_text = "According to ancient folklore and local legends, celestial birds fought here."
        self.assertEqual(classify_claim(folklore_text), "folklore_oral_tradition")

        documented_text = "Archaeological Survey of India reports document that the granite pillar was built in 1530 AD."
        self.assertEqual(classify_claim(documented_text), "documented_history")

        personal_text = "We visited early in the morning and bought nice momos from the friendly uncle."
        self.assertEqual(classify_claim(personal_text), "community_experience")

    def test_detect_missing_fields(self):
        incomplete_place = {
            "short_description": "A quiet viewpoint.",
            "detailed_story": "Very pretty place to look at.",
            "practical_tips": [],
            "source_url": ""
        }
        missing = detect_missing_fields(incomplete_place)
        self.assertIn("Exact opening hours unverified", missing)
        self.assertIn("Entry fee / ticket details not verified", missing)
        self.assertIn("Original web source link pending", missing)

    def test_duplicate_detection(self):
        existing = [
            {"name": "Galu Devi Sunset Trail", "destination": "Naddi, Dharamshala"},
            {"name": "The Hanging Pillar", "destination": "Lepakshi, Andhra Pradesh"}
        ]
        is_dup, matched = is_duplicate_place("Galu Devi Trail", "Dharamshala", existing)
        self.assertTrue(is_dup)
        self.assertEqual(matched["name"], "Galu Devi Sunset Trail")

        is_dup2, _ = is_duplicate_place("Taj Mahal", "Agra", existing)
        self.assertFalse(is_dup2)

class TestRecommendationEngine(unittest.TestCase):
    def test_rank_places_query_relevance(self):
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
        ranked = rank_places(places, query="Sarojini", category_filter="markets_shopping")
        self.assertEqual(ranked[0]["name"], "Sarojini Nagar Export Lane")
        self.assertGreater(ranked[0]["relevance_score"], ranked[1]["relevance_score"])
        self.assertIn("score_breakdown", ranked[0])

    def test_rank_places_completeness_bonus(self):
        sparse = {
            "name": "Sparse Point",
            "destination": "Goa",
            "category": "nature_scenic",
            "short_description": "A place.",
            "detailed_story": "Small text.",
            "practical_tips": [],
            "budget_tier": "free",
            "source_type": "stored_archive"
        }
        rich = {
            "name": "Rich Historical Cove",
            "destination": "Goa",
            "category": "nature_scenic",
            "short_description": "A well documented quiet cove with historic coconut palms.",
            "detailed_story": "Extensive cultural and geographical breakdown of this seaside gem.",
            "practical_tips": ["Visit at low tide", "Bring reef shoes", "Respect local fishing nets"],
            "budget_tier": "free",
            "source_url": "https://example.com/source",
            "source_type": "stored_archive"
        }
        ranked = rank_places([sparse, rich], query="Goa")
        self.assertEqual(ranked[0]["name"], "Rich Historical Cove")
        self.assertGreater(
            ranked[0]["score_breakdown"]["information_completeness"],
            ranked[1]["score_breakdown"]["information_completeness"]
        )

class TestDatabaseAndSeeding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()

    def test_database_seeded_records(self):
        from app.database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM places")
        count = cur.fetchone()["count"]
        conn.close()
        self.assertGreaterEqual(count, 10)

    def test_search_pipeline_execution(self):
        import asyncio
        from app.routers.discovery import execute_search
        
        # Test search execution for Lepakshi
        result = asyncio.run(execute_search(destination="Lepakshi", q="pillar"))
        self.assertGreater(result.total_results, 0)
        self.assertTrue(any("Lepakshi" in r.destination for r in result.results))
        self.assertIsNotNone(result.results[0].relevance_score)
        self.assertIn("tinyfish_status", result.model_dump())

    def test_community_contribution_submission(self):
        from app.database import get_db_connection
        from app.routers.contributions import submit_contribution
        from app.schemas import ContributionCreate
        import asyncio

        data = ContributionCreate(
            place_name="Athangudi Tile Atelier",
            destination="Karaikudi, Chettinad",
            category="culture_history",
            contribution_type="experience_story",
            details="Artisanal glass-cast floral tiles made by master Chettinad craftsmen.",
            practical_tips="Visit morning hours",
            source_reference="Field visit",
            contributor_name="Explorer Priya"
        )
        res = asyncio.run(submit_contribution(data))
        self.assertGreater(res.id, 0)
        self.assertEqual(res.status, "pending")

if __name__ == "__main__":
    unittest.main(verbosity=2)
