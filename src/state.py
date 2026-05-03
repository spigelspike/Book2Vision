"""Shared application state and configuration for Book2Vision."""

import os
from src.library import LibraryManager


# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "temp_upload")
OUTPUT_DIR = os.path.join(BASE_DIR, "Book2Vision_Output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize Library Manager
library_manager = LibraryManager(UPLOAD_DIR)

# File Upload Security Configuration
MAX_FILE_SIZE_MB = 50  # Maximum upload size in MB
ALLOWED_EXTENSIONS = {".pdf", ".epub", ".txt"}
ALLOWED_MIMETYPES = {"application/pdf", "application/epub+zip", "text/plain"}


class AppState:
    """
    WARNING: This is a global singleton shared across all users.
    Concurrent users will overwrite each other's data.
    For production, implement per-session state or database persistence.
    """
    def __init__(self):
        self.ingestion_result = None
        self.analysis_result = None
        self.full_text = ""
        self.images_list = []
        self.entity_images = {}
        self.book_id = None
        self.audiobook_path = None
        self.immersive_audio_paths = []
        self.voice_sample_path = None
        self.colab_url = None


state = AppState()
