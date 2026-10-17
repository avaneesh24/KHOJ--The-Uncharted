import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from app.database import get_db_connection
from app.schemas import SearchResponse, PlaceResponse, SearchRequest
from app.services.tinyfish_service import tinyfish_service
from app.services.data_processor import is_duplicate_place, VALID_CATEGORIES
from app.services.recommendation_engine import rank_places

logger = logging.getLogger("khoj.discovery")
router = APIRouter(prefix="/discovery", tags=["Discovery & Search"])

def row_to_place_dict(row) -> Dict[str, Any]:
    """Converts a SQLite row to a Python dictionary with deserialized JSON lists."""
    d = dict(row)
    try:
        d["practical_tips"] = json.loads(d.get("practical_tips", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["practical_tips"] = []
    try:
        d["missing_fields_flag"] = json.loads(d.get("missing_fields_flag", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["missing_fields_flag"] = []
    d["is_approved"] = bool(d.get("is_approved", 1))
    return d

async def execute_search(
    q: Optional[str] = "",
    destination: Optional[str] = "",
    category: Optional[str] = None,
    budget: Optional[str] = None
) -> SearchResponse:
    """Core discovery search implementation used by GET and POST routes."""
    clean_q = (q or "").strip()
    clean_dest = (destination or "").strip()

    # 1. Fetch relevant places from local database
    conn = get_db_connection()
    cursor = conn.cursor()

    query_sql = "SELECT * FROM places WHERE is_approved = 1"
    params = []

    if clean_dest:
        query_sql += " AND (LOWER(destination) LIKE ? OR LOWER(name) LIKE ?)"
        params.extend([f"%{clean_dest.lower()}%", f"%{clean_dest.lower()}%"])

    if category and category != "all":
        query_sql += " AND category = ?"
        params.append(category)

    if budget and budget != "all":
        query_sql += " AND budget_tier = ?"
        params.append(budget)

    # If general search term provided and no specific destination filter
    if clean_q and not clean_dest:
        query_sql += " AND (LOWER(name) LIKE ? OR LOWER(short_description) LIKE ? OR LOWER(detailed_story) LIKE ? OR LOWER(destination) LIKE ?)"
        params.extend([f"%{clean_q.lower()}%", f"%{clean_q.lower()}%", f"%{clean_q.lower()}%", f"%{clean_q.lower()}%"])

    query_sql += " ORDER BY upvotes DESC LIMIT 50"
    cursor.execute(query_sql, params)
    rows = cursor.fetchall()
    conn.close()

    stored_places = [row_to_place_dict(r) for r in rows]

    # 2. Trigger TinyFish live web retrieval if destination or query is specified
    live_places = []
    tinyfish_status = tinyfish_service.get_status()

    if clean_dest or clean_q:
        target_search_dest = clean_dest if clean_dest else clean_q
        live_results, tf_meta = await tinyfish_service.retrieve_live_discoveries(
            destination=target_search_dest,
            query=clean_q,
            category=category
        )
        tinyfish_status.update(tf_meta)

        # 3. Deduplication: Merge or discard duplicates against stored database
        for live_item in live_results:
            is_dup, matched_item = is_duplicate_place(live_item["name"], live_item["destination"], stored_places)
            if not is_dup:
                live_item["id"] = 9000 + len(live_places)  # Temporary ID for live-session item
                live_places.append(live_item)
            else:
                logger.info(f"Deduplicated live item '{live_item['name']}' against existing record '{matched_item['name']}'")

    # Combine all candidate places
    all_candidates = live_places + stored_places

    # 4. Rank using transparent Python recommendation rules
    ranked_places = rank_places(
        places=all_candidates,
        query=f"{clean_dest} {clean_q}".strip(),
        category_filter=category,
        budget_filter=budget
    )

    return SearchResponse(
        query=clean_q,
        destination=clean_dest,
        category_filter=category,
        budget_filter=budget,
        total_results=len(ranked_places),
        live_retrieved_count=len(live_places),
        stored_count=len(stored_places),
        tinyfish_status=tinyfish_status,
        results=ranked_places
    )

@router.get("/search", response_model=SearchResponse)
async def search_discoveries_get(
    q: Optional[str] = Query("", description="Search keywords (e.g. 'sunset ridge', 'kachori')"),
    destination: Optional[str] = Query("", description="City or region (e.g. 'Dharamshala', 'Lepakshi', 'Delhi')"),
    category: Optional[str] = Query(None, description="Category filter (culture_history, local_food, etc.)"),
    budget: Optional[str] = Query(None, description="Budget tier filter (free, budget, moderate, splurge)")
):
    """GET endpoint for local discovery search."""
    return await execute_search(q=q, destination=destination, category=category, budget=budget)

@router.post("/search", response_model=SearchResponse)
async def search_discoveries_post(req: SearchRequest):
    """POST endpoint for local discovery search."""
    return await execute_search(q=req.query, destination=req.destination, category=req.category, budget=req.budget)

# Backward-compatible alias
search_discoveries = search_discoveries_get

@router.get("/destinations")
async def get_featured_destinations():
    """Returns curated destinations available in KHOJ knowledge base."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT destination, COUNT(*) as place_count,
        GROUP_CONCAT(DISTINCT category) as categories
        FROM places
        GROUP BY destination
        ORDER BY place_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    destinations = []
    for r in rows:
        destinations.append({
            "destination": r["destination"],
            "place_count": r["place_count"],
            "categories": r["categories"].split(",") if r["categories"] else []
        })
    return {"destinations": destinations}

@router.get("/categories")
async def get_categories():
    """Returns the standardized KHOJ taxonomy and counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM places
        GROUP BY category
    """)
    rows = cursor.fetchall()
    conn.close()

    counts = {r["category"]: r["count"] for r in rows}
    categories_list = []
    for cat_id, title in VALID_CATEGORIES.items():
        categories_list.append({
            "id": cat_id,
            "title": title,
            "count": counts.get(cat_id, 0)
        })
    return {"categories": categories_list}
