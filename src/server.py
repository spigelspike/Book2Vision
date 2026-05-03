"""Book2Vision API  FastAPI application entry point.

This module sets up the FastAPI app, middleware, and includes all route modules.
Endpoint logic lives in src/routers/.
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force load env vars
import src.config

from src.state import BASE_DIR, UPLOAD_DIR
from src.routers import upload_router, generation_router, content_router, library_router


# ============================================================================
# APP LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up Book2Vision...")
    print("Access the application at: http://localhost:8000")
    # Validate critical env vars
    if not os.getenv("GEMINI_API_KEY"):
        print("  CRITICAL WARNING: GEMINI_API_KEY is not set. AI features will fail.")
    else:
        print(" GEMINI_API_KEY found.")
    
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("  WARNING: DEEPSEEK_API_KEY is not set. Podcast generation will use fallback scripts.")
    else:
        print(" DEEPSEEK_API_KEY found.")

    if not os.getenv("DEAPI_API_KEY"):
        print("  WARNING: DEAPI_API_KEY is not set. High-quality image generation will fail.")
    else:
        print(" DEAPI_API_KEY found.")
    yield


app = FastAPI(title="Book2Vision API", lifespan=lifespan)


# ============================================================================
# MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' https://pollinations.ai https://image.pollinations.ai https://ui-avatars.com data:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint with API key status."""
    from src.config import GEMINI_API_KEY, DEEPSEEK_API_KEY, ELEVENLABS_API_KEY, DEEPGRAM_API_KEY
    
    return {
        "status": "ok", 
        "service": "book2vision",
        "api_keys": {
            "gemini": bool(GEMINI_API_KEY),
            "deepseek": bool(DEEPSEEK_API_KEY),
            "elevenlabs": bool(ELEVENLABS_API_KEY),
            "deepgram": bool(DEEPGRAM_API_KEY)
        }
    }


# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(content_router)
app.include_router(library_router)


# ============================================================================
# STATIC FILES
# ============================================================================

# Serve Static Assets (Uploaded/Generated)
app.mount("/api/assets", StaticFiles(directory=UPLOAD_DIR), name="assets")

# Serve Frontend
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Server starting... Open your browser at http://localhost:{port}")
    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)
