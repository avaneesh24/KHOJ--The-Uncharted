import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from seed_data import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    seed_database()

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "KHOJ — The Uncharted"
    assert data["status"] == "healthy"
    assert "tinyfish_configured" in data
    assert "database" in data

def test_search_discoveries():
    # Search for Dharamshala
    response = client.get("/api/discovery/search?destination=Dharamshala")
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] > 0
    assert any("Naddi" in r["destination"] or "Dharamshala" in r["destination"] for r in data["results"])
    assert "tinyfish_status" in data
    assert "relevance_score" in data["results"][0]

def test_search_categories():
    response = client.get("/api/discovery/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) >= 5

def test_get_place_detail():
    # Search first to get a real ID
    search_res = client.get("/api/discovery/search?q=Veerabhadra")
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert len(results) > 0
    place_id = results[0]["id"]

    detail_res = client.get(f"/api/places/{place_id}")
    assert detail_res.status_code == 200
    place = detail_res.json()
    assert place["id"] == place_id
    assert "practical_tips" in place
    assert isinstance(place["practical_tips"], list)
    assert "detailed_story" in place

def test_place_upvote():
    search_res = client.get("/api/discovery/search")
    place_id = search_res.json()["results"][0]["id"]

    res = client.post(f"/api/places/{place_id}/upvote")
    assert res.status_code == 200
    assert res.json()["place_id"] == place_id
    assert "upvotes" in res.json()

def test_submit_contribution():
    payload = {
        "place_name": "Chettinad Athangudi Tile Factory Walk",
        "destination": "Chettinad, Tamil Nadu",
        "category": "local_experiences",
        "contribution_type": "experience_story",
        "details": "Visiting the artisanal handmade glass-frame cement tile ateliers in Athangudi village.",
        "practical_tips": "Ask artisans for permission before recording video. Free entry.",
        "source_reference": "Tamil Nadu Heritage Collective",
        "contributor_name": "Ravi Swaminathan"
    }
    response = client.post("/api/contributions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["place_name"] == payload["place_name"]
    assert data["status"] == "pending"

def test_submit_feedback():
    payload = {
        "place_id": 1,
        "place_name": "Galu Devi Sunset Trail",
        "report_type": "outdated_info",
        "notes": "The village road had minor repairs recently; path is now smoother."
    }
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "received"

def test_api_search_post():
    payload = {
        "destination": "Lepakshi",
        "query": "hanging pillar",
        "category": "culture_history"
    }
    response = client.post("/api/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] > 0
    assert any("Lepakshi" in r["destination"] for r in data["results"])

def test_api_search_get():
    response = client.get("/api/search?destination=Delhi&category=markets_shopping")
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] > 0
    assert any("Sarojini" in r["name"] for r in data["results"])

def test_list_places_endpoint():
    response = client.get("/api/places?limit=5")
    assert response.status_code == 200
    places = response.json()
    assert isinstance(places, list)
    assert len(places) > 0
    assert "slug" in places[0]

def test_list_contributions_and_feedback():
    c_res = client.get("/api/contributions")
    assert c_res.status_code == 200
    assert isinstance(c_res.json(), list)

    f_res = client.get("/api/feedback")
    assert f_res.status_code == 200
    assert isinstance(f_res.json(), list)

def test_html_web_client_served():
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert "text/html" in home_res.headers["content-type"]
    assert "KHOJ" in home_res.text

    place_res = client.get("/place")
    assert place_res.status_code == 200
    assert "text/html" in place_res.headers["content-type"]
