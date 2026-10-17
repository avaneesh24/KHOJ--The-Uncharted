import json
from fastapi import APIRouter, HTTPException, Path
from app.database import get_db_connection
from app.schemas import PlaceResponse
from app.routers.discovery import row_to_place_dict

router = APIRouter(prefix="/places", tags=["Places Detail"])

@router.get("", response_model=list[PlaceResponse])
async def list_places(category: str = None, destination: str = None, limit: int = 20):
    """Returns a list of curated local discoveries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM places WHERE is_approved = 1"
    params = []
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)
    if destination:
        query += " AND LOWER(destination) LIKE ?"
        params.append(f"%{destination.lower()}%")
    query += " ORDER BY upvotes DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_place_dict(r) for r in rows]

@router.get("/{place_id}", response_model=PlaceResponse)
async def get_place_detail(place_id: int = Path(..., description="Unique ID of the place")):
    """
    Returns full details for a place:
    - Detailed story & cultural context
    - Distinguishes documented history from folklore/belief
    - Practical tips
    - Source link and retrieval timestamp
    - Explicit missing field notices
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places WHERE id = ?", (place_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Place with id {place_id} was not found.")

    place_dict = row_to_place_dict(row)
    return place_dict

@router.post("/{place_id}/upvote")
async def upvote_place(place_id: int = Path(..., description="Unique ID of the place")):
    """Allows travellers to upvote a helpful discovery."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE places SET upvotes = upvotes + 1 WHERE id = ?", (place_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Place not found.")
    
    cursor.execute("SELECT upvotes FROM places WHERE id = ?", (place_id,))
    new_upvotes = cursor.fetchone()["upvotes"]
    conn.commit()
    conn.close()
    return {"message": "Upvote recorded successfully", "place_id": place_id, "upvotes": new_upvotes}
