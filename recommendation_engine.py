import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

def compute_query_relevance(query: str, place: Dict[str, Any]) -> tuple[float, List[str]]:
    """
    Computes query relevance score (0 - 35 points).
    Checks token overlap across name, destination, description, tips, and story.
    """
    if not query or not query.strip():
        return 20.0, ["Broad discovery search (neutral query score)"]

    query_clean = query.lower().strip()
    query_tokens = [w for w in re.split(r'[^a-zA-Z0-9]+', query_clean) if len(w) > 2]
    if not query_tokens:
        return 20.0, ["Broad discovery search"]

    score = 0.0
    factors = []

    name = place.get("name", "").lower()
    dest = place.get("destination", "").lower()
    desc = place.get("short_description", "").lower()
    story = place.get("detailed_story", "").lower()
    tips = " ".join(place.get("practical_tips", [])).lower()

    # Exact phrase match in name
    if query_clean in name:
        score += 20.0
        factors.append(f"Exact query match in place name (+20.0)")
    elif any(token in name for token in query_tokens):
        score += 14.0
        factors.append(f"Keyword matched in place name (+14.0)")

    # Destination match
    if any(token in dest for token in query_tokens):
        score += 10.0
        factors.append(f"Destination match '{dest}' (+10.0)")

    # Description and story matches
    content_matches = sum(1 for token in query_tokens if token in desc or token in story)
    if content_matches > 0:
        token_pts = min(8.0, content_matches * 3.0)
        score += token_pts
        factors.append(f"{content_matches} keyword(s) found in story context (+{token_pts:.1f})")

    # Practical tips match
    if any(token in tips for token in query_tokens):
        score += 3.0
        factors.append("Keyword found in traveller tips (+3.0)")

    final_score = min(35.0, score)
    return final_score, factors

def compute_category_alignment(category_filter: Optional[str], place_cat: str) -> tuple[float, str]:
    """Computes category interest alignment (0 - 25 points)."""
    if not category_filter or category_filter == "all":
        return 18.0, "All categories explored (+18.0 neutral baseline)"
    if category_filter.lower() == place_cat.lower():
        return 25.0, f"Exact match with requested category (+25.0)"
    return 5.0, "Different category (+5.0 exploratory weight)"

def compute_completeness_score(place: Dict[str, Any]) -> tuple[float, List[str]]:
    """Computes information completeness score (0 - 20 points)."""
    score = 0.0
    factors = []

    tips = place.get("practical_tips", [])
    if len(tips) >= 3:
        score += 8.0
        factors.append("3+ practical tips available (+8.0)")
    elif len(tips) > 0:
        score += 5.0
        factors.append(f"{len(tips)} practical tip(s) available (+5.0)")

    story_len = len(place.get("detailed_story", ""))
    if story_len > 250:
        score += 6.0
        factors.append("Rich historical/cultural story narrative (+6.0)")
    elif story_len > 80:
        score += 3.0
        factors.append("Basic context available (+3.0)")

    if place.get("source_url"):
        score += 4.0
        factors.append("Verified public source link (+4.0)")

    missing = place.get("missing_fields_flag", [])
    if len(missing) <= 1:
        score += 2.0
        factors.append("Minimal unverified caveats (+2.0)")

    return min(20.0, score), factors

def compute_freshness_score(place: Dict[str, Any]) -> tuple[float, str]:
    """Computes source freshness and credibility (0 - 15 points)."""
    source_type = place.get("source_type", "")
    if source_type == "live_tinyfish":
        return 15.0, "Live retrieval via TinyFish web scrape (+15.0)"
    elif source_type == "community_verified":
        return 12.0, "Community verified contribution (+12.0)"
    elif source_type == "stored_archive":
        return 10.0, "Stored community archive (+10.0)"
    return 8.0, "Curated benchmark entry (+8.0)"

def compute_budget_match(budget_filter: Optional[str], place_budget: str) -> tuple[float, str]:
    """Computes budget alignment (0 - 5 points)."""
    if not budget_filter or budget_filter == "all":
        return 4.0, "Open budget (+4.0)"
    if budget_filter.lower() == place_budget.lower():
        return 5.0, f"Matches requested budget tier ({place_budget}) (+5.0)"
    return 2.0, "Different budget tier (+2.0)"

def rank_places(
    places: List[Dict[str, Any]],
    query: str = "",
    category_filter: Optional[str] = None,
    budget_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Ranks discovery items using transparent, rule-based scoring.
    Returns sorted list with score breakdowns and human-readable explanations.
    """
    scored_places = []

    for place in places:
        q_score, q_factors = compute_query_relevance(query, place)
        cat_score, cat_factor = compute_category_alignment(category_filter, place.get("category", ""))
        comp_score, comp_factors = compute_completeness_score(place)
        fresh_score, fresh_factor = compute_freshness_score(place)
        bud_score, bud_factor = compute_budget_match(budget_filter, place.get("budget_tier", "moderate"))

        total_score = round(q_score + cat_score + comp_score + fresh_score + bud_score, 1)

        explanation_parts = []
        if q_factors:
            explanation_parts.append(q_factors[0])
        explanation_parts.append(cat_factor)
        if comp_factors:
            explanation_parts.append(comp_factors[0])
        explanation_parts.append(fresh_factor)

        place_copy = dict(place)
        place_copy["relevance_score"] = total_score
        place_copy["score_breakdown"] = {
            "total_score": total_score,
            "query_relevance": round(q_score, 1),
            "category_match": round(cat_score, 1),
            "information_completeness": round(comp_score, 1),
            "source_freshness": round(fresh_score, 1),
            "budget_match": round(bud_score, 1),
            "explanation": " | ".join(explanation_parts)
        }
        scored_places.append(place_copy)

    # Sort descending by total score
    scored_places.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
    return scored_places
