#!/usr/bin/env python3
"""
KHOJ — The Uncharted: Local Discovery Platform
Main Application Server Runner

Usage:
    python run.py
"""

import sys
import os

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Switch working directory to backend so relative paths work seamlessly
os.chdir(BACKEND_DIR)

import uvicorn
from app.config import settings

def main():
    print("=" * 70)
    print("  🧭 KHOJ — The Uncharted | Discover Places. Uncover Stories.")
    print("  AZINHACK '26 Hackathon Edition")
    print("=" * 70)
    print(f"  • Web Application:  http://{settings.HOST}:{settings.PORT}")
    print(f"  • Interactive Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"  • Health Diagnostic: http://{settings.HOST}:{settings.PORT}/api/health")
    print(f"  • TinyFish Config:   {'Configured (Live Web Active)' if settings.has_tinyfish_key else 'Curated Knowledge Archive Mode (API key pending)'}")
    print(f"  • Database Engine:   {'SQLite (Local Persistent Storage)' if settings.is_sqlite else 'PostgreSQL'}")
    print("=" * 70)
    print("Starting server... Press Ctrl+C to terminate.")
    print()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()
