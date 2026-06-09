import os
import json
import time
import uuid
from typing import List, Dict, Optional
from pathlib import Path
from sqlmodel import Session, select
from src.database import engine, Book, Analysis, Image, init_db

class LibraryManager:
    """
    Manages the persistence of book metadata using SQLite.
    """
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Initialize DB
        init_db()
        
        # Migrate legacy JSON if needed
        self._migrate_legacy_json()
        self._check_schema_updates()
        self.scan_and_backfill()

    def _check_schema_updates(self):
        """Check for schema updates and apply them if needed."""
        try:
            from sqlalchemy import text
            with Session(engine) as session:
                # 1. Check if podcast_json column exists in analysis table
                result = session.exec(text("PRAGMA table_info(analysis)")).all()
                columns = [row[1] for row in result]
                
                if "podcast_json" not in columns:
                    print("INFO: Applying schema update: Adding podcast_json to analysis table...")
                    session.exec(text("ALTER TABLE analysis ADD COLUMN podcast_json VARCHAR"))
                    session.commit()
                    print("SUCCESS: Schema update complete.")

                # 2. Check if chapter table exists and create it if not
                # SQLModel.metadata.create_all handles table creation for new tables gracefully
                from src.database import SQLModel
                SQLModel.metadata.create_all(engine)
                
                # 3. Backfill chapters for existing books
                from src.database import Book, Chapter
                books = session.exec(select(Book)).all()
                for book in books:
                    if not book.full_text: continue
                    # Check if chapters already exist
                    existing_chapters = session.exec(select(Chapter).where(Chapter.book_id == book.id)).all()
                    if not existing_chapters:
                        print(f"INFO: Migrating book ID {book.id} to Chapter-Based Architecture...")
                        from src.text_sampler import split_into_chapters
                        chapters_data = split_into_chapters(book.full_text)
                        for ch_data in chapters_data:
                            new_chapter = Chapter(
                                book_id=book.id,
                                chapter_index=ch_data["index"],
                                title=ch_data["title"],
                                content=ch_data["content"]
                            )
                            session.add(new_chapter)
                        session.commit()
                        print(f"✅ Migrated book ID {book.id} ({len(chapters_data)} chapters created).")

        except Exception as e:
            print(f"⚠️ Schema update/migration failed: {e}")

    def _migrate_legacy_json(self):
        """Migrate data from library.json to SQLite."""
        json_path = os.path.join(self.project_root, "library.json")
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                books = json.load(f)
            
            with Session(engine) as session:
                for b in books:
                    # Check if exists
                    statement = select(Book).where(Book.filename == b["filename"])
                    existing = session.exec(statement).first()
                    if not existing:
                        # Create new book
                        new_book = Book(
                            title=b.get("title", "Unknown"),
                            author=b.get("author", "Unknown"),
                            filename=b.get("filename"),
                            full_text="" # Legacy books might not have text saved
                        )
                        session.add(new_book)
                        session.commit()
                        session.refresh(new_book)
                        
                        # If thumbnail exists, add as Image (cover)
                        if b.get("thumbnail"):
                            img = Image(
                                book_id=new_book.id,
                                type="cover",
                                path=b["thumbnail"]
                            )
                            session.add(img)
                session.commit()
            
            # Rename json to .bak to avoid re-migration
            os.rename(json_path, json_path + ".bak")
            print("✅ Migrated library.json to SQLite")
            
        except Exception as e:
            print(f"⚠️ Migration failed: {e}")

    def add_book(self, metadata: Dict, full_text: str = "") -> Dict:
        """
        Add a new book to the library.
        """
        try:
            with Session(engine) as session:
                # Check for duplicate filename
                statement = select(Book).where(Book.filename == metadata["filename"])
                existing = session.exec(statement).first()
                
                if existing:
                    # Update existing
                    existing.title = metadata.get("title", existing.title)
                    existing.author = metadata.get("author", existing.author)
                    existing.full_text = full_text or existing.full_text
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                    return self._book_to_dict(existing)
                
                new_book = Book(
                    title=metadata.get("title", "Unknown Title"),
                    author=metadata.get("author", "Unknown Author"),
                    filename=metadata.get("filename"),
                    full_text=full_text
                )
                session.add(new_book)
                session.commit()
                session.refresh(new_book)
                
                # Automatically chunk into chapters on ingest
                if full_text:
                    from src.database import Chapter
                    from src.text_sampler import split_into_chapters
                    chapters_data = split_into_chapters(full_text)
                    for ch_data in chapters_data:
                        new_chapter = Chapter(
                            book_id=new_book.id,
                            chapter_index=ch_data["index"],
                            title=ch_data["title"],
                            content=ch_data["content"]
                        )
                        session.add(new_chapter)
                    session.commit()
                    
                return self._book_to_dict(new_book)
        except Exception as e:
            print(f"❌ Error adding book to library: {e}")
            raise e

    def save_analysis(self, book_id: int, analysis_data: Dict):
        """Save analysis results to DB."""
        with Session(engine) as session:
            # Check if analysis exists
            statement = select(Analysis).where(Analysis.book_id == book_id)
            existing = session.exec(statement).first()
            
            summary = analysis_data.get("summary", "")
            entities = json.dumps(analysis_data.get("entities", []))
            scenes = json.dumps(analysis_data.get("scenes", []))
            keywords = json.dumps(analysis_data.get("keywords", []))
            podcast = json.dumps(analysis_data.get("podcast", [])) if analysis_data.get("podcast") else None
            
            if existing:
                existing.summary = summary
                existing.entities_json = entities
                existing.scenes_json = scenes
                existing.keywords_json = keywords
                if podcast:
                    existing.podcast_json = podcast
                session.add(existing)
            else:
                new_analysis = Analysis(
                    book_id=book_id,
                    summary=summary,
                    entities_json=entities,
                    scenes_json=scenes,
                    keywords_json=keywords,
                    podcast_json=podcast
                )
                session.add(new_analysis)
            session.commit()

    def save_podcast(self, book_id: int, playlist: List[Dict]):
        """Save podcast playlist to DB."""
        with Session(engine) as session:
            statement = select(Analysis).where(Analysis.book_id == book_id)
            existing = session.exec(statement).first()
            
            if existing:
                existing.podcast_json = json.dumps(playlist)
                session.add(existing)
                session.commit()
            else:
                # Should not happen if analysis exists, but just in case
                pass

    def get_chapters(self, book_id: int) -> List[Dict]:
        """Get all chapters for a book."""
        from src.database import Chapter
        with Session(engine) as session:
            statement = select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.chapter_index)
            chapters = session.exec(statement).all()
            return [
                {
                    "id": c.id,
                    "index": c.chapter_index,
                    "title": c.title,
                    "content_preview": (c.content[:200] + "...") if c.content else "",
                    "has_audio": bool(c.audio_playlist_json)
                }
                for c in chapters
            ]

    def get_chapter(self, chapter_id: int) -> Optional[Dict]:
        """Get a single chapter by ID."""
        from src.database import Chapter
        with Session(engine) as session:
            c = session.get(Chapter, chapter_id)
            if c:
                return {
                    "id": c.id,
                    "index": c.chapter_index,
                    "title": c.title,
                    "content": c.content,
                    "audio_playlist": json.loads(c.audio_playlist_json) if c.audio_playlist_json else []
                }
        return None

    def get_analysis(self, book_id: int) -> Optional[Dict]:
        """Get analysis results from DB."""
        with Session(engine) as session:
            statement = select(Analysis).where(Analysis.book_id == book_id)
            analysis = session.exec(statement).first()
            if analysis:
                return {
                    "summary": analysis.summary,
                    "entities": json.loads(analysis.entities_json),
                    "scenes": json.loads(analysis.scenes_json),
                    "scenes": json.loads(analysis.scenes_json),
                    "keywords": json.loads(analysis.keywords_json),
                    "podcast": json.loads(analysis.podcast_json) if analysis.podcast_json else []
                }
        return None

    def get_books(self) -> List[Dict]:
        """Get all books sorted by date (newest first)."""
        try:
            self.scan_and_backfill() # Ensure sync
            
            with Session(engine) as session:
                statement = select(Book).order_by(Book.upload_date.desc())
                books = session.exec(statement).all()
                return [self._book_to_dict(b, session) for b in books]
        except Exception as e:
            print(f"[WARNING] Error fetching library: {e}")
            return []

    def delete_book(self, book_id: int) -> bool:
        """Delete a book by ID."""
        with Session(engine) as session:
            book = session.get(Book, book_id)
            if not book:
                return False
            
            # Delete file
            file_path = os.path.join(self.upload_dir, book.filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            
            # Cascade delete is handled by SQLModel/SQLAlchemy if configured, 
            # but explicit delete is safer for now without cascade setup
            statement = select(Analysis).where(Analysis.book_id == book_id)
            analysis = session.exec(statement).first()
            if analysis:
                session.delete(analysis)
                
            # Delete images
            statement = select(Image).where(Image.book_id == book_id)
            images = session.exec(statement).all()
            for img in images:
                session.delete(img)
                
            session.delete(book)
            session.commit()
            return True

    def get_book(self, book_id: int) -> Optional[Dict]:
        """Get a single book by ID."""
        with Session(engine) as session:
            book = session.get(Book, book_id)
            return self._book_to_dict(book, session) if book else None

    def get_book_full_text(self, book_id: int) -> Optional[str]:
        """Get the full text of a book."""
        with Session(engine) as session:
            book = session.get(Book, book_id)
            return book.full_text if book else None

    def update_book_thumbnail(self, book_id: int, thumbnail_path: str) -> bool:
        """Update the thumbnail path for a book."""
        with Session(engine) as session:
            # Check if cover image exists
            statement = select(Image).where(Image.book_id == book_id).where(Image.type == "cover")
            existing = session.exec(statement).first()
            
            if existing:
                existing.path = thumbnail_path
                session.add(existing)
            else:
                img = Image(book_id=book_id, type="cover", path=thumbnail_path)
                session.add(img)
            session.commit()
            return True

    def update_book_digest(self, book_id: int, digest: str) -> bool:
        """Save a pre-computed digest to the book."""
        with Session(engine) as session:
            book = session.get(Book, book_id)
            if book:
                book.book_digest = digest
                session.add(book)
                session.commit()
                return True
        return False

    def save_chapter_audio(self, chapter_id: int, audio_path: str) -> bool:
        """Save the path to a generated chapter audio file."""
        from src.database import Chapter
        with Session(engine) as session:
            ch = session.get(Chapter, chapter_id)
            if ch:
                ch.audio_path = audio_path
                session.add(ch)
                session.commit()
                return True
        return False

    def _book_to_dict(self, book: Book, session: Session = None) -> Dict:
        """Convert Book model to dictionary for API."""
        # Get thumbnail
        thumbnail = None
        if session:
            # Use relationship if loaded, or query
            # Since we didn't eager load, query is safer
            statement = select(Image).where(Image.book_id == book.id).where(Image.type == "cover")
            img = session.exec(statement).first()
            if img:
                thumbnail = img.path
        
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "filename": book.filename,
            "upload_date": book.upload_date.timestamp(),
            "file_size": self._get_file_size(book.filename),
            "thumbnail": thumbnail,
            "book_digest": book.book_digest
        }

    def scan_and_backfill(self):
        """
        Scan upload directory for files not in library and add them.
        """
        if not os.path.exists(self.upload_dir):
            return

        with Session(engine) as session:
            existing_filenames = {b.filename for b in session.exec(select(Book)).all()}
            
            ALLOWED_EXTENSIONS = {".pdf", ".epub", ".txt"}
            
            count = 0
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ALLOWED_EXTENSIONS and filename not in existing_filenames:
                        # Found a new file!
                        print(f"Found unlisted book: {filename}")
                        new_book = Book(
                            title=filename,
                            author="Unknown",
                            filename=filename,
                            full_text=""
                        )
                        session.add(new_book)
                        count += 1
            
            if count > 0:
                session.commit()
                print(f"[SUCCESS] Backfilled {count} books into library")

    def _get_file_size(self, filename: str) -> int:
        if not filename: return 0
        try:
            return os.path.getsize(os.path.join(self.upload_dir, filename))
        except:
            return 0
