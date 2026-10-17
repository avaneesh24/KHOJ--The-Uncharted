import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Ensure backend root is on sys.path regardless of where server is started
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from app.config import settings
from app.database import init_db, check_db_health, get_db_connection
from app.services.tinyfish_service import tinyfish_service
from app.schemas import HealthResponse
from app.routers import discovery, places, contributions, feedback
from seed_data import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("khoj.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and seed if empty
    logger.info("Initializing KHOJ database...")
    init_db()
    
    # Check if places are seeded
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM places")
    count = cur.fetchone()["count"]
    conn.close()
    if count == 0:
        logger.info("Database empty; seeding initial discoveries...")
        seed_database()
    else:
        logger.info(f"Database contains {count} places.")

    logger.info(f"TinyFish configuration: configured={settings.has_tinyfish_key}")
    yield
    logger.info("Shutting down KHOJ application.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Community-driven local discovery platform. Discover lesser-known places, local stories, and practical travel tips.",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits Next.js dev server and direct browser access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(discovery.router, prefix=settings.API_PREFIX)
app.include_router(places.router, prefix=settings.API_PREFIX)
app.include_router(contributions.router, prefix=settings.API_PREFIX)
app.include_router(feedback.router, prefix=settings.API_PREFIX)

# Direct aliases for /api/search as requested by AZINHACK specifications
@app.get("/api/search", response_model=discovery.SearchResponse, tags=["Discovery & Search"])
async def api_search_alias_get(
    q: str = "",
    destination: str = "",
    category: str = None,
    budget: str = None
):
    return await discovery.execute_search(q=q, destination=destination, category=category, budget=budget)

@app.post("/api/search", response_model=discovery.SearchResponse, tags=["Discovery & Search"])
async def api_search_alias_post(req: discovery.SearchRequest):
    return await discovery.execute_search(q=req.query, destination=req.destination, category=req.category, budget=req.budget)

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check and integration diagnostics."""
    tf_status = tinyfish_service.get_status()
    db_health = check_db_health()

    return HealthResponse(
        app_name=settings.PROJECT_NAME,
        tagline=settings.TAGLINE,
        version=settings.VERSION,
        status="healthy" if db_health.get("status") == "healthy" else "degraded",
        tinyfish_configured=tf_status["is_configured"],
        tinyfish_mode=tf_status["mode"],
        database=db_health,
        timestamp=datetime.utcnow().isoformat()
    )

# Static files / Interactive web application
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse, tags=["Web Client"])
async def serve_app():
    """Serves the interactive KHOJ single-page web application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="""
    <html>
      <body style="font-family: sans-serif; padding: 40px; background: #F7F5EF; color: #123F3A;">
        <h1>KHOJ — The Uncharted</h1>
        <p>Discover Places. Uncover Stories.</p>
        <p>Backend API is active. Visit <a href="/docs">/docs</a> for the OpenAPI interactive documentation.</p>
      </body>
    </html>
    """)

@app.get("/place/{place_id}", response_class=HTMLResponse, tags=["Web Client"])
@app.get("/place", response_class=HTMLResponse, tags=["Web Client"])
async def serve_place_page(place_id: int = None):
    """Serves the standalone place detail page."""
    place_file = os.path.join(STATIC_DIR, "place.html")
    if os.path.exists(place_file):
        with open(place_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("Place detail template not found", status_code=404)
