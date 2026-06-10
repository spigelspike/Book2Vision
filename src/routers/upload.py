"""Upload & ingestion router for Book2Vision API."""

import os
import asyncio
import aiofiles
import mimetypes
import time
import traceback
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from src.state import state, UPLOAD_DIR, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS, ALLOWED_MIMETYPES, library_manager
from src.ingestion import ingest_book
from src.analysis import semantic_analysis
from src.visuals import generate_entity_image, generate_poster_with_deapi
from src.storage import upload_file_to_supabase

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    state.reset()
    try:
        # 1. Validate filename exists
        if not file.filename or file.filename == "":
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # 2. Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 3. Sanitize filename (prevent path traversal attacks)
        safe_filename = os.path.basename(file.filename)  # Strip any path components
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._- ")
        safe_filename = safe_filename.strip()
        
        if not safe_filename:
            safe_filename = f"upload_{int(time.time())}{file_ext}"
            
        import uuid
        safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 4. Check file size during streaming (prevent DoS)
        total_size = 0
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        
        async with aiofiles.open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    # File too large - clean up and reject
                    await buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
                    )
                await buffer.write(chunk)
        
        # 5. Verify MIME type after upload (content-based detection)
        detected_type, _ = mimetypes.guess_type(file_path)
        if detected_type not in ALLOWED_MIMETYPES:
            os.remove(file_path)  # Clean up invalid file
            raise HTTPException(
                status_code=400,
                detail=f"File content type not allowed: {detected_type}"
            )
        
        # Ingest
        try:
            ingestion_result = await ingest_book(file_path)
            
            # Clean up title if it accidentally pulled the UUID-prefixed filename
            import re
            raw_title = str(ingestion_result.get("title", ""))
            if re.match(r"^[0-9a-f]{8}[\s_]", raw_title, re.IGNORECASE):
                clean_title = raw_title[9:] # remove the 8-char UUID and space/underscore
                clean_title = clean_title.replace(".pdf", "").replace(".epub", "").replace(".txt", "")
                clean_title = clean_title.replace("_", " ").title()
                ingestion_result["title"] = clean_title
            ingestion_result["filename"] = safe_filename  # Use sanitized filename
        except Exception as e:
             print(f"Ingestion failed: {e}")
             # Clean up file on ingestion failure
             if os.path.exists(file_path):
                 os.remove(file_path)
             raise HTTPException(status_code=400, detail="File processing failed. Please ensure the file is a valid book format.")
        
        # Store state
        state.ingestion_result = ingestion_result
        state.full_text = ingestion_result.get("full_text", "")
        
        # Compute smart digest covering the full book
        from src.text_sampler import create_book_digest
        state.book_digest = create_book_digest(state.full_text)
        
        # Analysis — use the digest (covers full book) instead of raw text
        try:
            analysis = await semantic_analysis(state.book_digest)
            state.analysis_result = analysis
            
            # Pre-generation removed for performance. 
            # Frontend will lazy-load entity images via /api/entity_image/{name}
            print("Analysis complete. Entity images will be generated on demand.")

        except Exception as e:
            print(f"WARNING: Semantic analysis failed: {e}")
            # Fallback to empty analysis so app doesn't crash
            state.analysis_result = {"entities": [], "scenes": []}
            analysis = state.analysis_result

        
        # Upload to Supabase 'books' bucket
        remote_url = upload_file_to_supabase("books", file_path, safe_filename)
        # Fallback to local filename if upload fails
        final_filename = remote_url if remote_url else safe_filename

        # Add to library FIRST (so we have book_id)
        new_book = library_manager.add_book({
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown"),
            "filename": final_filename
        }, full_text=state.full_text)
        state.book_id = new_book["id"]
        
        # Save analysis to DB
        if state.analysis_result:
             library_manager.save_analysis(state.book_id, state.analysis_result)
        
        # Auto-generate cover in background (after book_id is set)
        title = ingestion_result.get("title", "Unknown")
        author = ingestion_result.get("author", "Unknown")
        
        # Allow generation for Extracted PDF but use filename as prompt
        should_generate = title and title != "Unknown"
        if title == "Extracted PDF":
            should_generate = True
            
        if should_generate:
            print(f"--- Scheduling cover generation for: {title}")
            
            async def generate_cover_background():
                try:
                    visuals_dir = os.path.join(UPLOAD_DIR, "visuals")
                    os.makedirs(visuals_dir, exist_ok=True)
                    
                    theme = ""
                    characters = analysis.get("entities", [])
                    
                    # Use filename if title is generic
                    gen_title = title
                    if title == "Extracted PDF" or title == "Book":
                         gen_title = safe_filename.replace("_", " ").replace(".pdf", "").replace(".epub", "")
                    
                    print(f"--- Starting cover generation for: {gen_title}")
                    cover_path = await generate_poster_with_deapi(
                        gen_title, author, visuals_dir, 
                        theme=theme, characters=characters
                    )
                    
                    if cover_path and state.book_id:
                        db_cover_path = cover_path
                        if not cover_path.startswith("http"):
                            db_cover_path = os.path.relpath(cover_path, UPLOAD_DIR).replace("\\", "/")
                        library_manager.update_book_thumbnail(state.book_id, db_cover_path)
                        print(f"SUCCESS: Auto-generated cover saved and linked to library: {db_cover_path}")

                    print(f"--- Generating top entities for: {gen_title}")
                    # Generate top 3 entities after cover
                    top_entities = characters[:3] if characters else []
                    entity_dir = os.path.join(UPLOAD_DIR, "entities")
                    os.makedirs(entity_dir, exist_ok=True)
                    
                    for entity in top_entities:
                        try:
                            # Parse entity — full format is [name, role, description, outfit, signature_prop]
                            if isinstance(entity, (list, tuple)) and len(entity) >= 2:
                                name = entity[0]
                                role = entity[1] if len(entity) > 1 else "Character"
                                description = entity[2] if len(entity) > 2 else ""
                                outfit = entity[3] if len(entity) > 3 else ""
                                signature_prop = entity[4] if len(entity) > 4 else ""
                            else:
                                name = str(entity)
                                role = "Character"
                                description = ""
                                outfit = ""
                                signature_prop = ""
                            
                            print(f"   Generating entity: {name}")
                            await generate_entity_image(
                                name, role, entity_dir,
                                description=description,
                                outfit=outfit,
                                signature_prop=signature_prop
                            )
                            await asyncio.sleep(1) # Add small breather to avoid Pollinations 429
                        except Exception as e:
                            print(f"WARNING: Failed to auto-generate entity {name}: {e}")
                    

                except Exception as e:
                    print(f"WARNING: Auto cover generation failed: {e}")
                    traceback.print_exc()
            
            # Add to background tasks
            background_tasks.add_task(generate_cover_background)
        
        return {
            "message": "Upload successful",
            "filename": final_filename,
            "analysis": analysis,
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Upload error: {type(e).__name__} - {e}")
        traceback.print_exc()  # Full trace in server logs only
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
