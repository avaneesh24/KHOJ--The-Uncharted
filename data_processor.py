import re
import difflib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

VALID_CATEGORIES = {
    "culture_history": "Culture & History",
    "local_food": "Local Food & Culinary",
    "markets_shopping": "Markets & Traditional Crafts",
    "nature_scenic": "Nature & Scenic Trails",
    "local_experiences": "Living Heritage & Local Tips"
}

CATEGORY_KEYWORDS = {
    "culture_history": [
        "temple", "monastery", "fort", "palace", "ruin", "heritage", "history", "ancient",
        "dynasty", "sculpture", "architecture", "monument", "shrine", "archaeological", "legend", "folklore"
    ],
    "local_food": [
        "food", "dish", "sweet", "chaat", "chai", "restaurant", "cafe", "dhaba", "thali",
        "cuisine", "bakery", "snack", "tasting", "street food", "culinary", "recipe", "bite"
    ],
    "markets_shopping": [
        "market", "bazaar", "shop", "handicraft", "textile", "pottery", "jewellery", "silk",
        "souvenir", "artisan", "flea market", "bargain", "antique", "craft", "fabric"
    ],
    "nature_scenic": [
        "waterfall", "sunset", "trail", "lake", "viewpoint", "valley", "hike", "peak",
        "forest", "river", "mountain", "cave", "hill", "meadow", "gorge", "wildlife"
    ],
    "local_experiences": [
        "walk", "village", "homestay", "workshop", "ritual", "festival", "community", "performance",
        "music", "dance", "traditional", "storytelling", "neighborhood", "art", "weaving"
    ]
}

FOLKLORE_KEYWORDS = [
    "legend", "myth", "folklore", "it is believed", "locals say", "according to lore",
    "mythology", "fable", "spiritual belief", "tale passed down", "oral history"
]

DOCUMENTED_KEYWORDS = [
    "asi", "archaeological survey of india", "built in", "century ad", "inscription",
    "charter", "gazetteer", "excavated", "recorded by", "dynasty records", "commissioned in"
]

def normalize_text(text: str) -> str:
    """Strips excessive whitespace and normalizes punctuation."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_name(raw_name: str) -> str:
    """Clean place name, removing SEO boilerplate prefixes and suffixes."""
    if not raw_name:
        return "Unnamed Discovery"
    cleaned = raw_name.strip()
    # Remove leading noise e.g., '10 Best Places to visit - '
    cleaned = re.sub(r'^(top\s+\d+(\s+places)?|best\s+\d+(\s+places)?|\d+\s+best(\s+places)?|\d+\s+top(\s+places)?|\d+\s+places\s+to\s+visit\s+in)\s*[-:–]\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[-|–]\s*(tripadvisor|holidify|wikipedia|travel guide|lonely planet|times of india|timesofindia|tripoto|culture trip|youtube|instagram).*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\.{2,}\s*$', '', cleaned)
    # Capitalize words properly
    words = cleaned.split()
    normalized = " ".join([w.capitalize() if not w.isupper() else w for w in words])
    return normalized[:150].strip()

def slugify(name: str, destination: str) -> str:
    """Generate a clean URL-friendly unique slug."""
    combo = f"{name} {destination}".lower()
    slug = re.sub(r'[^a-z0-9]+', '-', combo).strip('-')
    return slug[:180]

def map_category(raw_category: Optional[str], text_content: str = "") -> str:
    """
    Map an incoming freeform string or text snippet into standard KHOJ taxonomy.
    """
    if raw_category:
        norm_cat = raw_category.lower().strip()
        for key in VALID_CATEGORIES:
            if key in norm_cat:
                return key
        if any(w in norm_cat for w in ["food", "eat", "cafe", "dine", "tea"]):
            return "local_food"
        if any(w in norm_cat for w in ["experience", "village", "culture", "stay", "walk"]):
            return "local_experiences"
        if any(w in norm_cat for w in ["shop", "bazaar", "market", "handicraft"]):
            return "markets_shopping"
        if any(w in norm_cat for w in ["nature", "hike", "view", "lake", "scenic"]):
            return "nature_scenic"
        if any(w in norm_cat for w in ["temple", "history", "monument", "heritage", "fort"]):
            return "culture_history"

    # Analyze text content if category is missing or unknown
    combined = (text_content + " " + (raw_category or "")).lower()
    scores = {}
    for cat_id, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', combined))
        scores[cat_id] = score

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat
    return "local_experiences"

def classify_claim(text: str) -> str:
    """
    Distinguish documented history from folklore, local belief, or community experience.
    Ensures ethical, source-aware reporting of cultural and historical narratives.
    """
    lower = text.lower()
    has_folklore = any(kw in lower for kw in FOLKLORE_KEYWORDS)
    has_documented = any(kw in lower for kw in DOCUMENTED_KEYWORDS)

    if has_folklore and not has_documented:
        return "folklore_oral_tradition"
    if has_documented and not has_folklore:
        return "documented_history"
    if "legend" in lower or "belief" in lower:
        return "local_belief"
    return "community_experience"

def detect_missing_fields(place_data: Dict[str, Any]) -> List[str]:
    """
    Flag missing or unverified practical information instead of hallucinating.
    """
    missing = []
    text_content = (
        place_data.get("short_description", "") + " " +
        place_data.get("detailed_story", "") + " " +
        " ".join(place_data.get("practical_tips", []))
    ).lower()

    if not any(w in text_content for w in ["am", "pm", "timing", "hours", "opens at", "closes at", "sunrise", "sunset"]):
        missing.append("Exact opening hours unverified")

    if not any(w in text_content for w in ["free", "entry fee", "ticket", "rupees", "inr", "rs.", "cost", "price"]):
        missing.append("Entry fee / ticket details not verified")

    if not any(w in text_content for w in ["wheelchair", "accessible", "steps", "ramp", "stairs"]):
        missing.append("Physical accessibility status unverified")

    if not place_data.get("source_url"):
        missing.append("Original web source link pending")

    return missing

def is_duplicate_place(candidate_name: str, candidate_dest: str, existing_places: List[Dict[str, Any]], threshold: float = 0.78) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Fuzzy duplicate detection using Levenshtein / sequence matcher ratio.
    Prevents duplicate entries across web scrapers and user submissions.
    """
    clean_candidate = candidate_name.lower().strip()
    clean_dest = candidate_dest.lower().strip()

    for item in existing_places:
        item_dest = item.get("destination", "").lower().strip()
        # Same destination or region check
        if clean_dest in item_dest or item_dest in clean_dest or not clean_dest:
            existing_name = item.get("name", "").lower().strip()
            # Direct match
            if clean_candidate == existing_name:
                return True, item
            # Substring match for substantial names
            if len(clean_candidate) > 5 and len(existing_name) > 5:
                if clean_candidate in existing_name or existing_name in clean_candidate:
                    return True, item
            # Sequence matcher similarity
            sim = difflib.SequenceMatcher(None, clean_candidate, existing_name).ratio()
            if sim >= threshold:
                return True, item

    return False, None

def process_raw_discovery(raw_item: Dict[str, Any], default_destination: str = "") -> Optional[Dict[str, Any]]:
    """
    Validates, normalizes, and enriches a place item extracted from TinyFish or web retrieval.
    """
    raw_name = raw_item.get("name") or raw_item.get("title") or ""
    name = normalize_name(raw_name)
    if len(name) < 2:
        return None

    destination = raw_item.get("destination") or default_destination or "India"
    destination = normalize_text(destination)

    short_desc = normalize_text(raw_item.get("short_description") or raw_item.get("description") or raw_item.get("snippet") or "")
    if len(short_desc) < 10:
        short_desc = f"An interesting local spot to discover around {destination}."
    elif len(short_desc) > 480:
        short_desc = short_desc[:476].rsplit(" ", 1)[0] + "..."

    detailed_story = normalize_text(raw_item.get("detailed_story") or raw_item.get("story") or short_desc)
    category = map_category(raw_item.get("category"), f"{name} {short_desc} {detailed_story}")

    # Practical tips normalization
    tips = raw_item.get("practical_tips") or []
    if isinstance(tips, str):
        tips = [t.strip() for t in tips.split("\n") if t.strip()]
    tips = [normalize_text(t) for t in tips if len(t.strip()) > 3]

    claim_type = classify_claim(f"{name} {short_desc} {detailed_story}")
    budget_tier = raw_item.get("budget_tier", "moderate")
    if budget_tier not in ["free", "budget", "moderate", "splurge"]:
        budget_tier = "moderate"

    source_url = raw_item.get("source_url") or raw_item.get("url") or ""
    source_title = raw_item.get("source_title") or "Public Web Source"
    source_type = raw_item.get("source_type") or "live_tinyfish"

    temp_dict = {
        "name": name,
        "slug": slugify(name, destination),
        "category": category,
        "destination": destination,
        "short_description": short_desc,
        "detailed_story": detailed_story,
        "claim_type": claim_type,
        "practical_tips": tips,
        "budget_tier": budget_tier,
        "source_url": source_url,
        "source_title": source_title,
        "source_type": source_type,
        "retrieved_at": datetime.utcnow().isoformat(),
        "freshness_indicator": "fresh_live" if source_type == "live_tinyfish" else "recently_verified",
        "upvotes": 0,
        "is_approved": True,
        "created_at": datetime.utcnow().isoformat()
    }

    temp_dict["missing_fields_flag"] = detect_missing_fields(temp_dict)
    return temp_dict
