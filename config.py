import os
from typing import List
from dotenv import load_dotenv

# Search and load .env from project root and backend directory
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_root_dir = os.path.dirname(_backend_dir)

root_env = os.path.join(_root_dir, ".env")
backend_env = os.path.join(_backend_dir, ".env")

if os.path.exists(root_env):
    load_dotenv(dotenv_path=root_env)
if os.path.exists(backend_env):
    load_dotenv(dotenv_path=backend_env)
load_dotenv()

class Settings:
    PROJECT_NAME: str = "KHOJ — The Uncharted"
    TAGLINE: str = "Discover Places. Uncover Stories."
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # TinyFish API credentials (securely read from environment)
    @property
    def TINYFISH_API_KEY(self) -> str:
        return os.getenv("TINYFISH_API_KEY", "").strip()

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./khoj.db")

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # CORS
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]

    @property
    def has_tinyfish_key(self) -> bool:
        return bool(self.TINYFISH_API_KEY and len(self.TINYFISH_API_KEY) > 5)

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

settings = Settings()
