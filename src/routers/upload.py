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

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
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
        
        # Analysis
        try:
            analysis = await semantic_analysis(state.full_text)
            state.analysis_result = analysis
            
            # Pre-generation removed for performance. 
            # Frontend will lazy-load entity images via /api/entity_image/{name}
            print("Analysis complete. Entity images will be generated on demand.")

        except Exception as e:
            print(f"WARNING: Semantic analysis failed: {e}")
            # Fallback to empty analysis so app doesn't crash
            state.analysis_result = {"entities": [], "scenes": []}
            analysis = state.analysis_result

        
        # Add to library FIRST (so we have book_id)
        new_book = library_manager.add_book({
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown"),
            "filename": safe_filename
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
            print(f"🎨 Scheduling cover generation for: {title}")
            
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
                    
                    print(f"🎭 Generating top entities for: {gen_title}")
                    # Generate top 3 entities first (Sequential: Entities -> Cover)
                    top_entities = characters[:3] if characters else []
                    entity_dir = os.path.join(UPLOAD_DIR, "entities")
                    os.makedirs(entity_dir, exist_ok=True)
                    
                    for entity in top_entities:
                        try:
                            # Parse entity
                            if isinstance(entity, list) and len(entity) >= 2:
                                name, role = entity[0], entity[1]
                            elif isinstance(entity, tuple) and len(entity) >= 2:
                                name, role = entity[0], entity[1]
                            else:
                                name = str(entity)
                                role = "Character"
                            
                            print(f"   Generating entity: {name}")
                            await generate_entity_image(name, role, entity_dir)
                            # Small delay to prevent rate limiting
                            await asyncio.sleep(1)
                        except Exception as e:
                            print(f"⚠️ Failed to auto-generate entity {name}: {e}")

                    print(f"🎨 Starting cover generation for: {gen_title}")
                    cover_path = await generate_poster_with_deapi(
                        gen_title, author, visuals_dir, 
                        theme=theme, characters=characters
                    )
                    
                    if cover_path and state.book_id:
                        filename = os.path.basename(cover_path)
                        library_manager.update_book_thumbnail(state.book_id, f"visuals/{filename}")
                        print(f"✅ Auto-generated cover saved and linked to library: {cover_path}")
                except Exception as e:
                    print(f"⚠️ Auto cover generation failed: {e}")
                    traceback.print_exc()
            
            # Add to background tasks
            background_tasks.add_task(generate_cover_background)
        
        return {
            "message": "Upload successful",
            "filename": safe_filename,
            "analysis": analysis,
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {type(e).__name__} - {e}")
        traceback.print_exc()  # Full trace in server logs only
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
