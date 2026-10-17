import asyncio
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

def test_live_search_e2e():
    print("Testing End-to-End Live Search with TinyFish...")
    client = TestClient(app)

    # 1. Health endpoint test
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    print(f"Health response: configured={health_data.get('tinyfish_configured')}, mode={health_data.get('tinyfish_mode')}")
    assert health_data.get("tinyfish_configured") is True

    # 2. POST /api/search query with real destination
    search_payload = {
        "destination": "Lepakshi",
        "query": "Veerabhadra temple hanging pillar",
        "category": "culture_history"
    }
    
    response = client.post("/api/search", json=search_payload)
    assert response.status_code == 200
    data = response.json()

    print(f"Total results: {data.get('total_results')}")
    print(f"Live retrieved count: {data.get('live_retrieved_count')}")
    print(f"Stored count: {data.get('stored_count')}")
    print(f"TinyFish status: {data.get('tinyfish_status', {}).get('status')}")

    results = data.get("results", [])
    assert len(results) > 0

    # Check for live TinyFish results
    live_results = [r for r in results if r.get("source_type") == "live_tinyfish"]
    print(f"Live TinyFish items in response: {len(live_results)}")

    for i, item in enumerate(live_results[:3]):
        print(f"  [Live Item {i+1}]: {item.get('name')}")
        print(f"    Destination: {item.get('destination')}")
        print(f"    Source: {item.get('source_title')} ({item.get('source_url')[:50]}...)")
        print(f"    Claim: {item.get('claim_type')}")
        print(f"    Relevance Score: {item.get('relevance_score')}")

    assert len(live_results) > 0, "Expected at least 1 live TinyFish result!"
    print("\nSUCCESS: Real TinyFish Search & Fetch successfully integrated and returned to API!")

if __name__ == "__main__":
    test_live_search_e2e()
