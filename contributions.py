import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from app.database import get_db_connection
from app.schemas import ContributionCreate, ContributionResponse
from app.services.data_processor import (
    is_duplicate_place,
    normalize_name,
    slugify,
    map_category
)

router = APIRouter(prefix="/contributions", tags=["Community Contributions"])

@router.post("", response_model=ContributionResponse)
async def submit_contribution(data: ContributionCreate):
    """
    Submits a community discovery, local tip, or correction.
    Validated on backend and stored permanently in the database.
    New discoveries (new_place) are promoted into the places directory with duplicate prevention.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()

    # 1. Duplicate prevention for new place discoveries
    if data.contribution_type == "new_place":
        cursor.execute("SELECT name, destination FROM places")
        existing_places = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT place_name as name, destination FROM community_contributions WHERE contribution_type = 'new_place'")
        existing_contribs = [dict(r) for r in cursor.fetchall()]

        is_dup, matched = is_duplicate_place(data.place_name, data.destination, existing_places + existing_contribs)
        if is_dup:
            conn.close()
            matched_name = matched.get("name") if matched else data.place_name
            raise HTTPException(
                status_code=409,
                detail=f"A discovery matching '{data.place_name}' in '{data.destination}' already exists in KHOJ (similar to '{matched_name}')."
            )

    # 2. Record contribution in community_contributions table
    cursor.execute("""
    INSERT INTO community_contributions (
        place_name, destination, category, contribution_type, details,
        practical_tips, source_reference, contributor_name, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        data.place_name.strip(),
        data.destination.strip(),
        data.category.strip(),
        data.contribution_type,
        data.details.strip(),
        data.practical_tips or "",
        data.source_reference or "",
        data.contributor_name or "Anonymous Explorer",
        now_str
    ))
    new_id = cursor.lastrowid

    # 3. For new_place contributions, permanently insert into places table
    if data.contribution_type == "new_place":
        clean_name = normalize_name(data.place_name)
        base_slug = slugify(clean_name, data.destination)
        unique_slug = base_slug
        suffix = 1
        while True:
            cursor.execute("SELECT id FROM places WHERE slug = ?", (unique_slug,))
            if not cursor.fetchone():
                break
            suffix += 1
            unique_slug = f"{base_slug}-{suffix}"

        short_desc = data.details.strip()
        if len(short_desc) > 150:
            short_desc = short_desc[:146].rsplit(" ", 1)[0] + "..."

        mapped_cat = map_category(data.category, f"{clean_name} {data.details}")
        tips_list = [t.strip() for t in data.practical_tips.split("\n") if t.strip()] if data.practical_tips else []
        if not tips_list and data.practical_tips and data.practical_tips.strip():
            tips_list = [data.practical_tips.strip()]

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
            data.destination.strip(),
            short_desc,
            data.details.strip(),
            "community_experience",
            json.dumps(tips_list),
            "moderate",
            data.source_reference or "",
            f"Community by {data.contributor_name or 'Anonymous Explorer'}",
            "community_verified",
            now_str,
            "recently_verified",
            json.dumps([]),
            1,
            1,
            now_str
        ))

    conn.commit()
    conn.close()

    return ContributionResponse(
        id=new_id,
        place_name=data.place_name,
        destination=data.destination,
        category=data.category,
        contribution_type=data.contribution_type,
        details=data.details,
        practical_tips=data.practical_tips or "",
        source_reference=data.source_reference or "",
        contributor_name=data.contributor_name or "Anonymous Explorer",
        status="pending",
        created_at=now_str
    )

@router.get("", response_model=List[ContributionResponse])
async def list_contributions():
    """Lists recent community contributions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM community_contributions ORDER BY id DESC LIMIT 25")
    rows = cursor.fetchall()
    conn.close()

    return [ContributionResponse(**dict(r)) for r in rows]
