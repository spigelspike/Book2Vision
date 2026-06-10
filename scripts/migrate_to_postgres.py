import os
import sys
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import create_engine, Session, select, SQLModel
from src.database import Book, Chapter, Analysis, Image
from src.storage import upload_file_to_supabase
from src.config import DATABASE_URL
from src.state import UPLOAD_DIR

# 1. Local SQLite connection
local_url = "sqlite:///./library.db"
local_engine = create_engine(local_url)

# 2. Remote Postgres connection
# Check if the user really put DATABASE_URL in .env
if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    print("ERROR: DATABASE_URL is not set or is still pointing to sqlite.")
    print("Please make sure your .env has:")
    print("DATABASE_URL=postgresql://postgres.xxx:password@xxx.pooler.supabase.com:6543/postgres")
    sys.exit(1)

print(f"Connecting to Postgres: {DATABASE_URL.split('@')[-1]}")
remote_engine = create_engine(DATABASE_URL)

# Ensure tables exist in Postgres
SQLModel.metadata.create_all(remote_engine)

def migrate_data():
    with Session(local_engine) as local_db, Session(remote_engine) as remote_db:
        
        # 1. Migrate Books
        print("Migrating Books...")
        books = local_db.exec(select(Book)).all()
        book_id_map = {} # Map local ID to remote ID
        
        for local_book in books:
            print(f" Processing Book: {local_book.title}")
            
            # Upload local file to Supabase if it exists
            remote_filename = local_book.filename
            if local_book.filename and not local_book.filename.startswith("http"):
                local_path = os.path.join(UPLOAD_DIR, local_book.filename)
                if os.path.exists(local_path):
                    print(f"   Uploading local file to Supabase: {local_book.filename}")
                    new_url = upload_file_to_supabase("books", local_path, local_book.filename)
                    if new_url:
                        remote_filename = new_url
            
            remote_book = Book(
                title=local_book.title,
                author=local_book.author,
                filename=remote_filename,
                full_text=local_book.full_text,
                book_digest=local_book.book_digest,
                upload_date=local_book.upload_date
            )
            remote_db.add(remote_book)
            remote_db.commit()
            remote_db.refresh(remote_book)
            book_id_map[local_book.id] = remote_book.id
            
        # 2. Migrate Images
        print("Migrating Images...")
        images = local_db.exec(select(Image)).all()
        for img in images:
            if img.book_id not in book_id_map: continue
            
            remote_path = img.path
            if img.path and not img.path.startswith("http"):
                # Path might be absolute or relative like "visuals/..."
                filename = os.path.basename(img.path)
                local_path = img.path if os.path.isabs(img.path) else os.path.join(UPLOAD_DIR, img.path)
                
                if os.path.exists(local_path):
                    print(f"   Uploading local image to Supabase: {filename}")
                    new_url = upload_file_to_supabase("media", local_path, filename)
                    if new_url:
                        remote_path = new_url
            
            remote_img = Image(
                book_id=book_id_map[img.book_id],
                type=img.type,
                path=remote_path,
                prompt=img.prompt,
                created_at=img.created_at
            )
            remote_db.add(remote_img)
            
        # 3. Migrate Chapters
        print("Migrating Chapters...")
        chapters = local_db.exec(select(Chapter)).all()
        for ch in chapters:
            if ch.book_id not in book_id_map: continue
            
            remote_audio_path = ch.audio_path
            if ch.audio_path and not ch.audio_path.startswith("http"):
                filename = os.path.basename(ch.audio_path)
                local_path = ch.audio_path if os.path.isabs(ch.audio_path) else os.path.join(UPLOAD_DIR, ch.audio_path)
                if os.path.exists(local_path):
                    print(f"   Uploading local audio to Supabase: {filename}")
                    new_url = upload_file_to_supabase("media", local_path, filename)
                    if new_url:
                        remote_audio_path = new_url

            remote_ch = Chapter(
                book_id=book_id_map[ch.book_id],
                chapter_index=ch.chapter_index,
                title=ch.title,
                content=ch.content,
                audio_playlist_json=ch.audio_playlist_json,
                visuals_json=ch.visuals_json,
                analysis_json=ch.analysis_json,
                enhanced_script=ch.enhanced_script,
                audio_path=remote_audio_path
            )
            remote_db.add(remote_ch)
            
        # 4. Migrate Analysis
        print("Migrating Analysis...")
        analyses = local_db.exec(select(Analysis)).all()
        for an in analyses:
            if an.book_id not in book_id_map: continue
            remote_an = Analysis(
                book_id=book_id_map[an.book_id],
                summary=an.summary,
                entities_json=an.entities_json,
                scenes_json=an.scenes_json,
                keywords_json=an.keywords_json,
                podcast_json=an.podcast_json
            )
            remote_db.add(remote_an)
            
        remote_db.commit()
        print("Migration complete! All local files were uploaded to Supabase Storage and records transferred to Postgres.")

if __name__ == "__main__":
    migrate_data()
