import os
import json
import time
import uuid
from typing import List, Dict, Optional
from pathlib import Path

class LibraryManager:
    """
    Manages the persistence of book metadata.
    Stores data in library.json in the project root.
    """
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(self.project_root, "library.json")
        self.books: List[Dict] = []
        self.load_library()
        self.scan_and_backfill()

    def load_library(self):
        """Load library from JSON file."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.books = json.load(f)
                print(f"📚 Library loaded: {len(self.books)} books")
            except Exception as e:
                print(f"⚠️ Error loading library: {e}")
                self.books = []
        else:
            self.books = []

    def save_library(self):
        """Save library to JSON file."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.books, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving library: {e}")

    def add_book(self, metadata: Dict) -> Dict:
        """
        Add a new book to the library.
        metadata should contain: title, author, filename
        """
        book_id = str(uuid.uuid4())
        new_book = {
            "id": book_id,
            "title": metadata.get("title", "Unknown Title"),
            "author": metadata.get("author", "Unknown Author"),
            "filename": metadata.get("filename"),
            "upload_date": int(time.time()),
            "file_size": self._get_file_size(metadata.get("filename")),
            "thumbnail": None # Future: generate thumbnail
        }
        
        # Remove duplicates based on filename
        self.books = [b for b in self.books if b["filename"] != new_book["filename"]]
        
        self.books.insert(0, new_book) # Add to top
        self.save_library()
        return new_book

    def get_books(self) -> List[Dict]:
        """Get all books sorted by date (newest first)."""
        # Ensure file existence check
        valid_books = []
        changed = False
        for book in self.books:
            file_path = os.path.join(self.upload_dir, book["filename"])
            if os.path.exists(file_path):
                valid_books.append(book)
            else:
                changed = True
        
        if changed:
            self.books = valid_books
            self.save_library()
            
        return sorted(self.books, key=lambda x: x["upload_date"], reverse=True)

    def delete_book(self, book_id: str) -> bool:
        """Delete a book by ID (removes file and metadata)."""
        book = next((b for b in self.books if b["id"] == book_id), None)
        if not book:
            return False
            
        # Delete file
        file_path = os.path.join(self.upload_dir, book["filename"])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
        
        # Remove from list
        self.books = [b for b in self.books if b["id"] != book_id]
        self.save_library()
        return True

    def get_book(self, book_id: str) -> Optional[Dict]:
        """Get a single book by ID."""
        return next((b for b in self.books if b["id"] == book_id), None)

    def update_book_thumbnail(self, book_id: str, thumbnail_path: str) -> bool:
        """Update the thumbnail path for a book."""
        book = self.get_book(book_id)
        if book:
            book["thumbnail"] = thumbnail_path
            self.save_library()
            return True
        return False

    def scan_and_backfill(self):
        """
        Scan upload directory for files not in library and add them.
        """
        if not os.path.exists(self.upload_dir):
            return

        existing_filenames = {b["filename"] for b in self.books}
        
        # Allowed extensions from server.py
        ALLOWED_EXTENSIONS = {".pdf", ".epub", ".txt"}
        
        count = 0
        for filename in os.listdir(self.upload_dir):
            file_path = os.path.join(self.upload_dir, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in ALLOWED_EXTENSIONS and filename not in existing_filenames:
                    # Found a new file!
                    print(f"Found unlisted book: {filename}")
                    self.add_book({
                        "title": filename, # Temporary title
                        "author": "Unknown",
                        "filename": filename
                    })
                    count += 1
        
        if count > 0:
            print(f"✅ Backfilled {count} books into library")

    def _get_file_size(self, filename: str) -> int:
        if not filename: return 0
        try:
            return os.path.getsize(os.path.join(self.upload_dir, filename))
        except:
            return 0
