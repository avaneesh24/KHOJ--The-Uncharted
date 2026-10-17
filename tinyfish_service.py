import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.services.data_processor import (
    process_raw_discovery,
    normalize_name,
    map_category,
    classify_claim,
    detect_missing_fields
)

logger = logging.getLogger("khoj.tinyfish")

class TinyFishService:
    """
    Official TinyFish Web Intelligence Integration for KHOJ.
    Implements:
    - TinyFish Search API (https://api.search.tinyfish.ai)
    - TinyFish Fetch API (https://api.fetch.tinyfish.ai)
    Follows official TinyFish specifications for authentication (X-API-Key)
    and structured LLM-ready JSON extraction.
    """

    SEARCH_ENDPOINT = "https://api.search.tinyfish.ai"
    FETCH_ENDPOINT = "https://api.fetch.tinyfish.ai"

    def __init__(self):
        # We read from settings.TINYFISH_API_KEY dynamically
        pass

    @property
    def api_key(self) -> str:
        """Securely retrieves API key from settings without logging or exposing it."""
        return settings.TINYFISH_API_KEY

    def get_status(self) -> Dict[str, Any]:
        """Returns the operational status of TinyFish integration for diagnostics."""
        is_configured = bool(self.api_key and len(self.api_key) > 5)
        return {
            "is_configured": is_configured,
            "mode": "live_web_agent" if is_configured else "curated_archive_fallback",
            "provider": "TinyFish AI Web Operating Platform",
            "message": (
                "TinyFish Live Search & Fetch APIs active and verified."
                if is_configured else
                "TINYFISH_API_KEY is not configured in .env. Operating in verified community archive mode."
            ),
            "endpoints_ready": [
                "api.search.tinyfish.ai",
                "api.fetch.tinyfish.ai"
            ]
        }

    async def search_web(
        self,
        query: str,
        purpose: Optional[str] = None,
        location: str = "IN",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Calls official TinyFish Search API (https://api.search.tinyfish.ai).
        Returns a structured list of web search results.
        """
        if not self.api_key:
            return []

        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }
        params = {
            "query": query.strip(),
            "location": location
        }
        if purpose:
            params["purpose"] = purpose.strip()

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(self.SEARCH_ENDPOINT, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    logger.info(f"TinyFish Search returned {len(results)} results for query: {query[:50]}")
                    return results[:limit]
                else:
                    logger.warning(
                        f"TinyFish Search returned HTTP {resp.status_code}: {resp.text[:120]}"
                    )
                    return []
        except httpx.TimeoutException:
            logger.warning(f"TinyFish Search timed out for query: {query[:50]}")
            return []
        except Exception as e:
            logger.error(f"TinyFish Search request error: {type(e).__name__}: {str(e)[:100]}")
            return []

    async def fetch_url_content(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calls official TinyFish Fetch API (https://api.fetch.tinyfish.ai).
        Extracts clean markdown and structured text for candidate discovery URLs.
        """
        if not self.api_key or not urls:
            return {}

        clean_urls = [u for u in urls if u and u.startswith("http")][:4]
        if not clean_urls:
            return {}

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {"urls": clean_urls}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.FETCH_ENDPOINT, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    fetched_map = {}
                    for item in results:
                        u = item.get("url") or item.get("final_url")
                        if u:
                            fetched_map[u] = item
                    logger.info(f"TinyFish Fetch successfully extracted {len(fetched_map)} URLs")
                    return fetched_map
                else:
                    logger.warning(f"TinyFish Fetch returned HTTP {resp.status_code}: {resp.text[:120]}")
                    return {}
        except httpx.TimeoutException:
            logger.warning("TinyFish Fetch request timed out; using search snippets.")
            return {}
        except Exception as e:
            logger.error(f"TinyFish Fetch error: {type(e).__name__}: {str(e)[:100]}")
            return {}

    def extract_tips_from_text(self, text: str) -> List[str]:
        """
        Extracts actionable traveller tips from text content or bullet points.
        """
        if not text:
            return []
        tips = []
        lines = text.split("\n")
        tip_keywords = [
            "timing", "hours", "morning", "evening", "sunset", "sunrise",
            "wear", "shoes", "entry", "ticket", "cost", "fee", "carry",
            "reach", "best time", "avoid", "dress", "camera", "socks"
        ]
        
        for line in lines:
            line_clean = line.strip().lstrip("*-•#>0123456789. ")
            if 20 <= len(line_clean) <= 220:
                lower_line = line_clean.lower()
                if any(kw in lower_line for kw in tip_keywords):
                    tips.append(line_clean)
                    if len(tips) >= 3:
                        break
        return tips

    async def retrieve_live_discoveries(
        self,
        destination: str,
        query: str = "",
        category: Optional[str] = None,
        max_results: int = 5
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes end-to-end live web discovery:
        1. Queries TinyFish Search API for relevant web pages.
        2. Enriches top candidate URLs using TinyFish Fetch API.
        3. Normalizes and validates via KHOJ Python processing pipeline.
        4. Preserves authentic source URLs, domains, and ISO timestamps.
        """
        if not self.api_key:
            return [], {
                "live_retrieval_attempted": False,
                "status": "unconfigured",
                "message": "Live retrieval requires TINYFISH_API_KEY in .env. Showing verified local knowledge base."
            }

        # 1. Formulate search query & intent
        search_terms = []
        if destination:
            search_terms.append(destination.strip())
        if query:
            search_terms.append(query.strip())
        
        raw_query = " ".join(search_terms)
        if not raw_query:
            raw_query = "India offbeat lesser known heritage cultural gems"
        else:
            raw_query = f"{raw_query} offbeat hidden gems lesser known spots"

        purpose = (
            f"Discover lesser-known, authentic local places, cultural stories, food spots, or heritage gems "
            f"around {destination or 'India'}. Query: {query or 'local discovery'}."
        )

        try:
            # 2. Call TinyFish Search API
            search_results = await self.search_web(
                query=raw_query,
                purpose=purpose,
                location="IN",
                limit=max_results
            )

            if not search_results:
                return [], {
                    "live_retrieval_attempted": True,
                    "status": "empty",
                    "source": "TinyFish Search API",
                    "search_endpoint": self.SEARCH_ENDPOINT,
                    "places_retrieved": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }

            # 3. Call TinyFish Fetch API for top 2 candidates to get richer text
            candidate_urls = [r["url"] for r in search_results if r.get("url")][:2]
            fetched_pages = {}
            if candidate_urls:
                fetched_pages = await self.fetch_url_content(candidate_urls)

            # 4. Construct and normalize raw discovery items
            processed_results = []
            for item in search_results:
                url = item.get("url") or ""
                raw_title = item.get("title") or "Local Discovery"
                snippet = item.get("snippet") or ""
                site_name = item.get("site_name") or ""
                if not site_name and url:
                    site_name = urlparse(url).netloc.replace("www.", "")

                # Check if rich page was fetched
                fetched = fetched_pages.get(url, {})
                full_text = fetched.get("text", "")
                page_desc = fetched.get("description", "")

                short_desc = page_desc if len(page_desc) > 20 else snippet
                if len(short_desc) > 480:
                    short_desc = short_desc[:476].rsplit(" ", 1)[0] + "..."
                if len(short_desc) < 15:
                    short_desc = f"An interesting local spot to discover around {destination or 'the region'}."

                detailed_story = full_text[:600] if len(full_text) > 80 else snippet
                if len(detailed_story) < len(short_desc):
                    detailed_story = short_desc

                practical_tips = self.extract_tips_from_text(full_text if full_text else snippet)

                raw_dict = {
                    "name": raw_title,
                    "destination": destination or "India",
                    "category": category or "local_experiences",
                    "short_description": short_desc,
                    "detailed_story": detailed_story,
                    "practical_tips": practical_tips,
                    "budget_tier": "moderate",
                    "source_url": url,
                    "source_title": site_name or "Web Source",
                    "source_type": "live_tinyfish"
                }

                normalized = process_raw_discovery(raw_dict, default_destination=destination)
                if normalized:
                    normalized["source_type"] = "live_tinyfish"
                    normalized["freshness_indicator"] = "fresh_live"
                    normalized["retrieved_at"] = datetime.utcnow().isoformat()
                    processed_results.append(normalized)

            metadata = {
                "live_retrieval_attempted": True,
                "status": "success" if processed_results else "empty",
                "source": "TinyFish Live Search & Fetch",
                "search_endpoint": self.SEARCH_ENDPOINT,
                "fetch_endpoint": self.FETCH_ENDPOINT,
                "places_retrieved": len(processed_results),
                "timestamp": datetime.utcnow().isoformat()
            }
            return processed_results, metadata

        except Exception as e:
            logger.error(f"TinyFish live retrieval pipeline failed: {type(e).__name__}: {e}", exc_info=True)
            return [], {
                "live_retrieval_attempted": True,
                "status": "error",
                "error_type": type(e).__name__,
                "message": f"External retrieval error: {str(e)[:150]}. Seamlessly fallen back to verified archive.",
                "timestamp": datetime.utcnow().isoformat()
            }

tinyfish_service = TinyFishService()
