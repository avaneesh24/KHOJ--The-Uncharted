import asyncio
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings

async def test_live_connection():
    print(f"Testing TinyFish configuration...")
    print(f"has_tinyfish_key: {settings.has_tinyfish_key}")
    
    if not settings.has_tinyfish_key:
        print("FAIL: TINYFISH_API_KEY is not loaded or too short.")
        return False

    import httpx
    # 1. Test Search API
    search_url = "https://api.search.tinyfish.ai"
    headers = {"X-API-Key": settings.TINYFISH_API_KEY}
    params = {
        "query": "Lepakshi hanging pillar Andhra Pradesh history",
        "purpose": "Discover cultural stories and history of Lepakshi temple",
        "location": "IN"
    }
    
    print("\n--- 1. Testing TinyFish Search API ---")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(search_url, headers=headers, params=params)
            print(f"Search API HTTP status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                print(f"Search API success! Total results: {data.get('total_results', len(results))}")
                for i, r in enumerate(results[:3]):
                    print(f"  [{i+1}] {r.get('title')} ({r.get('site_name')}) -> {r.get('url')[:60]}...")
                
                # 2. Test Fetch API on top result URL
                if results and results[0].get("url"):
                    test_target_url = results[0]["url"]
                    print(f"\n--- 2. Testing TinyFish Fetch API on: {test_target_url[:60]}... ---")
                    fetch_url = "https://api.fetch.tinyfish.ai"
                    fetch_resp = await client.post(
                        fetch_url,
                        headers={"X-API-Key": settings.TINYFISH_API_KEY, "Content-Type": "application/json"},
                        json={"urls": [test_target_url]}
                    )
                    print(f"Fetch API HTTP status: {fetch_resp.status_code}")
                    if fetch_resp.status_code == 200:
                        fetch_data = fetch_resp.json()
                        fetch_results = fetch_data.get("results", [])
                        print(f"Fetch API success! Pages fetched: {len(fetch_results)}")
                        if fetch_results:
                            page = fetch_results[0]
                            text_snippet = page.get("text", "")[:120].replace("\n", " ")
                            print(f"  Fetched Title: {page.get('title')}")
                            print(f"  Fetched Content snippet: {text_snippet}...")
                        return True
                    else:
                        print(f"Fetch API response: {fetch_resp.text[:200]}")
                return True
            else:
                print(f"Search API failed with status {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"Error testing TinyFish API: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_live_connection())
    sys.exit(0 if success else 1)
