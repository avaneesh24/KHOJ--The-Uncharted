from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class PlaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="Name of the place or discovery spot")
    category: str = Field(..., description="Category identifier (e.g. culture_history, local_food)")
    destination: str = Field(..., min_length=2, max_length=200, description="Parent city or destination")
    short_description: str = Field(..., min_length=10, max_length=1000, description="Brief summary")
    detailed_story: str = Field(..., min_length=20, description="In-depth narrative, historical or cultural context")
    claim_type: str = Field(default="community_experience", description="documented_history, folklore_oral_tradition, local_belief, community_experience")
    practical_tips: List[str] = Field(default_factory=list, description="Actionable tips for travellers")
    budget_tier: str = Field(default="moderate", description="free, budget, moderate, splurge, unknown")
    source_url: str = Field(default="", description="Source link where information was discovered")
    source_title: str = Field(default="", description="Title or publication name of source")
    source_type: str = Field(default="stored_archive", description="live_tinyfish, stored_archive, community_verified, curated_sample")
    freshness_indicator: str = Field(default="recently_verified", description="fresh_live, recently_verified, archived")
    missing_fields_flag: List[str] = Field(default_factory=list, description="Explicit notices of unverified details")

class PlaceCreate(PlaceBase):
    pass

class PlaceResponse(PlaceBase):
    id: int
    slug: str
    retrieved_at: str
    upvotes: int = 0
    is_approved: bool = True
    created_at: str
    relevance_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: Optional[str] = Field(default="", description="Search keywords")
    destination: Optional[str] = Field(default="", description="Destination or region")
    category: Optional[str] = Field(default=None, description="Category filter")
    budget: Optional[str] = Field(default=None, description="Budget filter")

class SearchResponse(BaseModel):
    query: str
    destination: str
    category_filter: Optional[str] = None
    budget_filter: Optional[str] = None
    total_results: int
    live_retrieved_count: int
    stored_count: int
    tinyfish_status: Dict[str, Any]
    results: List[PlaceResponse]

class ContributionCreate(BaseModel):
    place_name: str = Field(..., min_length=2, max_length=200)
    destination: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, max_length=100)
    contribution_type: str = Field(..., description="new_place, local_tip, correction, experience_story")
    details: str = Field(..., min_length=15, max_length=2000)
    practical_tips: Optional[str] = Field(default="", max_length=1000)
    source_reference: Optional[str] = Field(default="", max_length=500)
    contributor_name: Optional[str] = Field(default="Anonymous Explorer", max_length=100)

class ContributionResponse(BaseModel):
    id: int
    place_name: str
    destination: str
    category: str
    contribution_type: str
    details: str
    practical_tips: str
    source_reference: str
    contributor_name: str
    status: str
    created_at: str

class FeedbackCreate(BaseModel):
    place_id: Optional[int] = None
    place_name: str = Field(..., min_length=2, max_length=200)
    report_type: str = Field(..., description="outdated_info, inaccurate_story, place_closed, incorrect_location, other")
    notes: str = Field(..., min_length=5, max_length=1000)

class FeedbackResponse(BaseModel):
    id: int
    place_id: Optional[int]
    place_name: str
    report_type: str
    notes: str
    created_at: str
    status: str = "received"

class HealthResponse(BaseModel):
    app_name: str
    tagline: str
    version: str
    status: str
    tinyfish_configured: bool
    tinyfish_mode: str
    database: Dict[str, Any]
    timestamp: str
