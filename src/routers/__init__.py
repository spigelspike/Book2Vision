"""Router package for Book2Vision API."""

from src.routers.upload import router as upload_router
from src.routers.generation import router as generation_router
from src.routers.content import router as content_router
from src.routers.library import router as library_router

__all__ = [
    "upload_router",
    "generation_router",
    "content_router",
    "library_router",
]
