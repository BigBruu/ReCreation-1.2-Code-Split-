import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


def require_min_length_env(name: str, minimum: int) -> str:
    value = require_env(name)
    if len(value.encode("utf-8")) < minimum:
        raise RuntimeError(f"{name} must be at least {minimum} bytes long")
    return value


MONGO_URL = require_env("MONGO_URL")
DB_NAME = require_env("DB_NAME")
SECRET_KEY = require_min_length_env("SECRET_KEY", 32)
ADMIN_PASSWORD = require_env("ADMIN_PASSWORD")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", str(24 * 60)))


def get_cors_origins() -> list[str]:
    configured = os.environ.get("CORS_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    origins = {
        "http://localhost:5000",
        "http://0.0.0.0:5000",
    }

    for domain_value in (os.environ.get("REPLIT_DEV_DOMAIN", ""), os.environ.get("REPLIT_DOMAINS", "")):
        for domain in domain_value.replace(",", " ").split():
            domain = domain.strip()
            if domain:
                origins.add(f"https://{domain}")

    return sorted(origins)