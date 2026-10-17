import os
import sys
import sqlite3
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.database import DB_FILE, get_db_connection

def run_persistence_flow_verification():
    print("=" * 70)
    print("KHOJ COMMUNITY DISCOVERY PERSISTENCE VERIFICATION")
    print("=" * 70)

    client = TestClient(app)

    # Clean up any previous test record for idempotency
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM places WHERE name = 'Persistence Test Park'")
    c.execute("DELETE FROM community_contributions WHERE place_name = 'Persistence Test Park'")
    conn.commit()
    conn.close()

    # -------------------------------------------------------------
    # Step 1: Add a new discovery called "Persistence Test Park"
    # -------------------------------------------------------------
    print("\n[Step 1] Submitting 'Persistence Test Park' via POST /api/contributions...")
    payload = {
        "place_name": "Persistence Test Park",
        "destination": "Delhi",
        "category": "nature_scenic",
        "contribution_type": "new_place",
        "details": "A tranquil neighborhood green space with jogging paths, seasonal blooms, and peaceful morning bird songs.",
        "practical_tips": "Best visited during early mornings 6:00 AM to 8:30 AM. Ample shade and bench seating available.",
        "source_reference": "Verified Resident Field Visit",
        "contributor_name": "Explorer Neeru"
    }

    res = client.post("/api/contributions", json=payload)
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    contrib_id = data["id"]
    print(f"Success! Contribution recorded with ID #{contrib_id}")

    # -------------------------------------------------------------
    # Step 2: Confirm the backend successfully saves it to SQLite
    # -------------------------------------------------------------
    print("\n[Step 2] Confirming persistent database records in SQLite...")
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check community_contributions
    c.execute("SELECT * FROM community_contributions WHERE id = ?", (contrib_id,))
    contrib_row = c.fetchone()
    assert contrib_row is not None, "Contribution record missing from community_contributions table!"
    print(f"  -> Found in 'community_contributions': id={contrib_row['id']}, place='{contrib_row['place_name']}', status='{contrib_row['status']}'")

    # Check places table
    c.execute("SELECT * FROM places WHERE name = 'Persistence Test Park'")
    place_row = c.fetchone()
    assert place_row is not None, "Discovery missing from 'places' table!"
    print(f"  -> Found in 'places': id={place_row['id']}, name='{place_row['name']}', source_type='{place_row['source_type']}', is_approved={place_row['is_approved']}")
    assert place_row["source_type"] == "community_verified", f"Expected source_type 'community_verified', got '{place_row['source_type']}'"
    assert place_row["is_approved"] == 1, "Expected is_approved=1"
    conn.close()

    # -------------------------------------------------------------
    # Step 3: Refresh the website (Simulate page refresh / initial load)
    # -------------------------------------------------------------
    print("\n[Step 3] Simulating website refresh (executeSearch with empty query/destination)...")
    search_res = client.post("/api/search", json={
        "query": "",
        "destination": "",
        "category": "all",
        "budget": "all"
    })
    assert search_res.status_code == 200
    search_data = search_res.json()
    all_places = search_data.get("results", [])

    matched = [p for p in all_places if p["name"] == "Persistence Test Park"]
    assert len(matched) == 1, f"Expected Persistence Test Park in refreshed results, found: {len(matched)}"
    park = matched[0]
    print(f"  -> Verified: '{park['name']}' returned on page refresh!")
    print(f"  -> Source Type: '{park['source_type']}'")
    print(f"  -> Relevance Score: {park['relevance_score']} pts")
    assert park["source_type"] == "community_verified"

    # -------------------------------------------------------------
    # Step 4: Duplicate Submission Prevention Test
    # -------------------------------------------------------------
    print("\n[Step 4] Testing duplicate submission prevention...")
    dup_res = client.post("/api/contributions", json=payload)
    print(f"Duplicate submission status code: {dup_res.status_code}")
    assert dup_res.status_code == 409, f"Expected 409 Conflict, got {dup_res.status_code}: {dup_res.text}"
    print(f"  -> Verified duplicate rejection message: {dup_res.json().get('detail')}")

    # -------------------------------------------------------------
    # Step 5: Restart the backend and check again
    # -------------------------------------------------------------
    print("\n[Step 5] Simulating backend restart (fresh client & re-initialized lifespan)...")
    fresh_client = TestClient(app)
    restart_res = fresh_client.post("/api/search", json={
        "query": "",
        "destination": ""
    })
    assert restart_res.status_code == 200
    restart_places = restart_res.json().get("results", [])
    restart_matched = [p for p in restart_places if p["name"] == "Persistence Test Park"]
    assert len(restart_matched) == 1, "Persistence Test Park lost after simulated backend restart!"
    print(f"  -> Verified: '{restart_matched[0]['name']}' safely retained across server restart!")

    # -------------------------------------------------------------
    # Step 6: Run a TinyFish search & verify saved discovery is not lost
    # -------------------------------------------------------------
    print("\n[Step 6] Running search queries to confirm discovery is not lost or mislabeled...")
    
    # Search specifically for the park
    park_search_res = fresh_client.post("/api/search", json={
        "query": "Persistence Test Park",
        "destination": "Delhi"
    })
    assert park_search_res.status_code == 200
    park_search_data = park_search_res.json()
    park_hits = [p for p in park_search_data.get("results", []) if "Persistence Test Park" in p["name"]]
    assert len(park_hits) > 0, "Could not find park when searching by name!"
    print(f"  -> Direct search found '{park_hits[0]['name']}' with source_type='{park_hits[0]['source_type']}'")
    assert park_hits[0]["source_type"] == "community_verified", "Community discovery was mislabeled!"

    # TinyFish search for an external destination (Lepakshi)
    tf_res = fresh_client.post("/api/search", json={
        "destination": "Lepakshi",
        "query": "Veerabhadra pillar"
    })
    assert tf_res.status_code == 200
    tf_data = tf_res.json()
    print(f"  -> TinyFish search returned {tf_data.get('total_results')} results ({tf_data.get('live_retrieved_count')} live scrapes).")

    # Verify that the saved park is STILL in the database and was not erased by TinyFish search
    verify_conn = get_db_connection()
    vc = verify_conn.cursor()
    vc.execute("SELECT id, name, source_type FROM places WHERE name = 'Persistence Test Park'")
    saved_after_tf = vc.fetchone()
    assert saved_after_tf is not None, "TinyFish search erased or corrupted the saved community discovery!"
    print(f"  -> Confirmed in DB after TinyFish search: id={saved_after_tf['id']}, name='{saved_after_tf['name']}', source_type='{saved_after_tf['source_type']}'")
    verify_conn.close()

    print("\n" + "=" * 70)
    print("ALL 6 PERSISTENCE FLOW VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_persistence_flow_verification()
