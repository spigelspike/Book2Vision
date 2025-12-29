import os
import shutil
import uvicorn
import aiofiles
import mimetypes
import traceback
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import time

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion import ingest_book, clean_format
from src.analysis import semantic_analysis
from src.audio import generate_audio as generate_audio_service
from src.visuals import generate_images, generate_entity_image
from src.knowledge import generate_quizzes, ask_question, suggest_questions
from src.podcast import generate_podcast_script, generate_podcast_audio
from src.library import LibraryManager

app = FastAPI(title="Book2Vision API")

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # CSP: Allow self, Pollinations images, inline styles (glassmorphism), self scripts
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

# CORS - Restrict to specific origins
# For development: localhost only
# For production: Set ALLOWED_ORIGINS env var to your domain(s)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Specific origins only (not "*")
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only needed methods
    allow_headers=["Content-Type", "Authorization"],  # Specific headers
)

@app.on_event("startup")
async def startup_event():
    print("Starting up Book2Vision...")
    print("Access the application at: http://localhost:8000")
    # Validate critical env vars
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  CRITICAL WARNING: GEMINI_API_KEY is not set. AI features will fail.")
    else:
        print("✅ GEMINI_API_KEY found.")
    
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  WARNING: DEEPSEEK_API_KEY is not set. Podcast generation will use fallback scripts.")
    else:
        print("✅ DEEPSEEK_API_KEY found.")

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

# State (Simple in-memory for demo)
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

state = AppState()

# Models
class AudioRequest(BaseModel):
    text: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM" # Rachel
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    provider: str = "elevenlabs" # elevenlabs, deepgram, inbuilt

class VisualsRequest(BaseModel):
    style: str = "storybook"
    seed: int = 42

class QARequest(BaseModel):
    question: str

# Endpoints

@app.post("/api/upload")
async def upload_book(file: UploadFile = File(...)):
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
            ingestion_result = ingest_book(file_path)
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
            analysis = semantic_analysis(state.full_text)
            state.analysis_result = analysis
            
            # Pre-generation removed for performance. 
            # Frontend will lazy-load entity images via /api/entity_image/{name}
            print("Analysis complete. Entity images will be generated on demand.")

        except Exception as e:
            print(f"WARNING: Semantic analysis failed: {e}")
            # Fallback to empty analysis so app doesn't crash
            state.analysis_result = {"entities": [], "summary": "Analysis failed due to API error.", "scenes": []}
            analysis = state.analysis_result


        
        # Add to library
        new_book = library_manager.add_book({
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown"),
            "filename": safe_filename
        })
        state.book_id = new_book["id"]
        
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
        print(f"Upload error: {type(e).__name__} - {e}")
        traceback.print_exc()  # Full trace in server logs only
        raise HTTPException(status_code=500, detail="File upload failed. Please try again or contact support.")

@app.get("/api/story")
async def get_story():
    if not state.ingestion_result:
        raise HTTPException(status_code=404, detail="No book uploaded")
    
    return {
        "body": state.ingestion_result.get("body", ""),
        "entities": state.analysis_result.get("entities", []) if state.analysis_result else [],
        "images": state.images_list
    }

@app.post("/api/generate/audio")
async def generate_audio(req: AudioRequest):
    try:
        print(f"=== Audio Generation Request ===")
        print(f"Text length: {len(req.text)}")
        print(f"Voice ID: {req.voice_id}")
        
        if not req.text:
             raise HTTPException(status_code=400, detail="No text provided for audio generation")

        # For demo, just use preview text
        preview_text = req.text[:2000]
        
        # Use unique filename to prevent caching
        timestamp = int(time.time())
        filename = f"audiobook_{timestamp}.mp3"
        output_path = os.path.join(UPLOAD_DIR, filename)
        
        print(f"Calling generate_audio_service...")
        
        audio_file = await generate_audio_service(
            preview_text, 
            output_path, 
            voice_id=req.voice_id,
            stability=req.stability,
            similarity_boost=req.similarity_boost,
            style=req.style,
            use_speaker_boost=req.use_speaker_boost,
            provider=req.provider
        )
        
        if not audio_file:
             print("ERROR: generate_audio_service returned None")
             raise HTTPException(status_code=500, detail="Audio generation failed. Check server logs.")
        
        print(f"Audio file created: {audio_file}")
        return {"audio_url": f"/api/assets/{filename}"}
    except HTTPException:
        raise
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"=== AUDIO GENERATION ERROR ===")
        print(error_details)
        
        provider = req.provider  # Get the requested provider
        
        # Check for common errors (don't expose detailed exception info)
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            if provider == "elevenlabs":
                raise HTTPException(status_code=500, detail="ElevenLabs API Key is invalid or missing.")
            elif provider == "deepgram":
                raise HTTPException(status_code=500, detail="Deepgram API Key is invalid or missing.")
            else:
                raise HTTPException(status_code=500, detail="Authentication failed for audio provider.")
        if "quota" in error_str or "limit" in error_str:
            raise HTTPException(status_code=500, detail=f"{provider.title()} quota exceeded or rate limit reached.")
        
        # Generic error (don't leak exception details)
        raise HTTPException(status_code=500, detail="Audio generation failed. Please try again or contact support.")

@app.post("/api/generate/visuals")
async def generate_visuals(req: VisualsRequest, background_tasks: BackgroundTasks):
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="Analyze book first")
    
    # Add validation
    if not state.analysis_result.get("scenes") and not state.analysis_result.get("entities"):
        raise HTTPException(status_code=400, detail="Analysis did not produce scenes or entities for visualization")
        
    try:
        visuals_dir = os.path.join(UPLOAD_DIR, "visuals")
        # Clean directory to prevent mixing with old images
        if os.path.exists(visuals_dir):
            shutil.rmtree(visuals_dir)
        os.makedirs(visuals_dir, exist_ok=True)
        
        # Get title - prefer filename if title is generic
        title = state.ingestion_result.get("title", "Unknown") if state.ingestion_result else "Book"
        if title in ["Unknown", "Extracted PDF", "Book"] and state.ingestion_result.get("filename"):
             title = state.ingestion_result.get("filename")
        
        # Prepare list of expected images so frontend knows what to wait for
        # We need to replicate the logic from generate_images briefly to get filenames
        expected_images = []
        
        # 1. Title
        safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
        expected_images.append(f"image_00_title_{safe_title}.jpg")
        
        # 2. Scenes
        scenes = state.analysis_result.get("scenes", [])
        for i in range(len(scenes)):
            expected_images.append(f"image_01_scene_{i+1:02d}.jpg")
            
        # 3. Entities (Top 3)
        entities = state.analysis_result.get("entities", [])
        top_entities = entities[:3]
        for i, entity in enumerate(top_entities):
            if isinstance(entity, list) and len(entity) >= 1:
                name = entity[0]
            elif isinstance(entity, tuple) and len(entity) >= 1:
                name = entity[0]
            else:
                name = str(entity)
            safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
            expected_images.append(f"image_02_entity_{safe_name}.jpg")
            
        # Update state with expected paths (relative)
        state.images_list = [os.path.join(visuals_dir, img) for img in expected_images]
        
        # Start background generation
        background_tasks.add_task(generate_images, state.analysis_result, visuals_dir, style=req.style, seed=req.seed, title=title)
        
        # Update thumbnail in library (use first scene if available, else title)
        if state.book_id:
            thumbnail_filename = None
            scenes = state.analysis_result.get("scenes", [])
            if len(scenes) > 0:
                 thumbnail_filename = f"image_01_scene_01.jpg"
            elif len(expected_images) > 0:
                 thumbnail_filename = expected_images[0]
            
            if thumbnail_filename:
                # Store relative path from upload dir (which is what library expects/serves via assets)
                # Actually library stores metadata. Frontend constructs URL.
                # Let's store "visuals/filename.jpg"
                library_manager.update_book_thumbnail(state.book_id, f"visuals/{thumbnail_filename}")

        # Return relative paths for frontend immediately
        image_urls = [f"/api/assets/visuals/{img}" for img in expected_images]
        return {"images": image_urls, "status": "generating"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Visuals generation error: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate visuals. Please try again.")

@app.get("/api/entity_image/{name}")
async def get_entity_image(name: str, role: str = "Character", regenerate: bool = False):
    # Check cache unless regenerating
    if not regenerate and name in state.entity_images:
        return {"image_url": f"/api/assets/entities/{os.path.basename(state.entity_images[name])}"}
        
    try:
        img_dir = os.path.join(UPLOAD_DIR, "entities")
        os.makedirs(img_dir, exist_ok=True)
        
        # If regenerating, maybe use a new seed or just re-call
        seed = None if regenerate else 42
        
        img_path = await generate_entity_image(name, role, img_dir, seed=seed)
        
        if img_path:
            state.entity_images[name] = img_path
            # Add timestamp to URL to bust browser cache
            return {"image_url": f"/api/assets/entities/{os.path.basename(img_path)}?t={int(time.time())}"}
        else:
            return {"image_url": None}
    except Exception as e:
        print(f"Entity image error: {e}")
        return {"image_url": None}

@app.post("/api/qa")
async def qa_endpoint(req: QARequest):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
    
    try:
        answer = ask_question(state.full_text, req.question)
        return {"answer": answer}
    except Exception as e:
        print(f"QA Error: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Question answering failed. Please try again.")

@app.get("/api/suggested_questions")
async def suggested_questions_endpoint():
    if not state.full_text:
        return {"questions": []}
        
    try:
        questions = suggest_questions(state.full_text)
        return {"questions": questions}
    except Exception as e:
        print(f"Suggested questions error: {e}")
        return {"questions": []}

@app.post("/api/generate/podcast")
async def generate_podcast_endpoint(background_tasks: BackgroundTasks):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
        
    try:
        print("="*50)
        print("🎙️  PODCAST GENERATION STARTED")
        print(f"Book text length: {len(state.full_text)} characters")
        print("="*50)
        
        # 1. Generate Script
        print("📝 Step 1: Generating script...")
        script = await generate_podcast_script(state.full_text)
        
        # Check if script is error fallback
        is_error_fallback = (
            len(script) == 5 and 
            any("trouble on our end" in seg.get("text", "") or 
                "hiccup on our end" in seg.get("text", "") for seg in script)
        )
        
        if is_error_fallback:
            error_msg = "Script generation failed. "
            # Try to extract error details from script
            for seg in script:
                text = seg.get("text", "")
                if "Error:" in text:
                    error_msg += text
                    break
            print(f"⚠️  {error_msg}")
            # Still continue but log warning
        
        print(f"✅ Script generated: {len(script)} segments")
        
        # 2. Generate Audio
        print("🎵 Step 2: Generating audio...")
        podcast_dir = os.path.join(UPLOAD_DIR, "podcast")
        audio_files = await generate_podcast_audio(script, podcast_dir)
        
        if not audio_files:
            raise HTTPException(status_code=500, detail="Audio generation failed - no files created")
        
        print(f"✅ Audio generated: {len(audio_files)} files")
        
        # 3. Return playlist
        # Format: [{"speaker": "Jax", "url": "/api/assets/podcast/..."}]
        playlist = []
        for i, filename in enumerate(audio_files):
            if i < len(script):  # Safety check
                speaker = script[i]["speaker"]
                playlist.append({
                    "speaker": speaker,
                    "text": script[i]["text"],
                    "url": f"/api/assets/podcast/{filename}"
                })
        
        print("="*50)
        print(f"✅ PODCAST GENERATION COMPLETE: {len(playlist)} segments")
        print("="*50)
            
        return {"playlist": playlist}
    except HTTPException:
        raise
    except Exception as e:
        print("="*50)
        print("❌ PODCAST GENERATION ERROR")
        print(f"Error: {e}")
        traceback.print_exc()
        print("="*50)
        
        # Provide more specific error messages
        error_str = str(e).lower()
        if "deepseek" in error_str or "api" in error_str:
            raise HTTPException(
                status_code=500, 
                detail="Podcast script generation failed. Check DeepSeek API key and quota."
            )
        elif "audio" in error_str:
            raise HTTPException(
                status_code=500,
                detail="Audio generation failed. Check TTS provider configuration."
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Podcast generation failed: {str(e)[:100]}"
            )

# Library Endpoints

@app.get("/api/library")
async def get_library():
    """Get all books in the library."""
    return {"books": library_manager.get_books()}

@app.delete("/api/library/{book_id}")
async def delete_book(book_id: str):
    """Delete a book from the library."""
    success = library_manager.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}

@app.post("/api/library/load/{book_id}")
async def load_book(book_id: str):
    """Load a book from the library into active state."""
    state.book_id = book_id
    book = library_manager.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    filename = book["filename"]
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        # Clean up if file is missing
        library_manager.delete_book(book_id)
        raise HTTPException(status_code=404, detail="Book file not found on server")
    
    try:
        # Re-ingest (fast, mostly reading text)
        # In a real app, we'd cache the analysis too, but re-analyzing is safer for now
        ingestion_result = ingest_book(file_path)
        ingestion_result["filename"] = filename
        
        # Update state
        state.ingestion_result = ingestion_result
        state.full_text = ingestion_result.get("full_text", "")
        
        # Re-analyze
        # Optimization: We could store analysis in a JSON file alongside the book
        # For now, let's re-run analysis to ensure fresh state
        print(f"Reloading book: {book['title']}...")
        analysis = semantic_analysis(state.full_text)
        state.analysis_result = analysis
        
        return {
            "message": "Book loaded successfully",
            "filename": filename,
            "analysis": analysis,
            "title": book["title"],
            "author": book["author"]
        }
    except Exception as e:
        print(f"Error loading book: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load book: {str(e)}")

# Serve Static Assets (Uploaded/Generated)
app.mount("/api/assets", StaticFiles(directory=UPLOAD_DIR), name="assets")

# Serve Frontend
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Server starting... Open your browser at http://localhost:{port}")
    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)
