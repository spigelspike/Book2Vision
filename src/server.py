import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion import ingest_book, clean_format
from src.analysis import semantic_analysis
from src.audio import generate_audio as generate_audio_service
from src.visuals import generate_images, generate_entity_image
from src.knowledge import generate_quizzes, ask_question, suggest_questions

app = FastAPI(title="Book2Vision API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Starting up Book2Vision...")
    print("Access the application at: http://localhost:8000")
    # Validate critical env vars
    if not os.getenv("GEMINI_API_KEY"):
        print("CRITICAL WARNING: GEMINI_API_KEY is not set. AI features will fail.")
    else:
        print("GEMINI_API_KEY found.")

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify service status.
    """
    return {"status": "ok", "service": "book2vision"}

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "temp_upload")
OUTPUT_DIR = os.path.join(BASE_DIR, "Book2Vision_Output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# State (Simple in-memory for demo)
class AppState:
    def __init__(self):
        self.ingestion_result = None
        self.analysis_result = None
        self.full_text = ""
        self.images_list = []
        self.entity_images = {}

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
    """
    Uploads a book (PDF, EPUB, TXT), ingests it, and performs initial analysis.
    Returns the book metadata and analysis results.
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest
        try:
            ingestion_result = ingest_book(file_path)
            ingestion_result["filename"] = file.filename
        except Exception as e:
             print(f"Ingestion failed: {e}")
             raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
        
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

        return {
            "message": "Upload successful",
            "filename": file.filename,
            "analysis": analysis,
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/story")
async def get_story():
    """
    Retrieves the full text of the book and the current analysis state.
    """
    if not state.ingestion_result:
        raise HTTPException(status_code=404, detail="No book uploaded")
    
    return {
        "body": state.ingestion_result.get("body", ""),
        "entities": state.analysis_result.get("entities", []) if state.analysis_result else [],
        "images": state.images_list
    }

@app.post("/api/generate/audio")
async def generate_audio(req: AudioRequest):
    """
    Generates an audiobook segment from the provided text using the selected provider.
    Returns a URL to the generated audio file.
    """
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
        # Check for common errors
        if "401" in str(e):
             raise HTTPException(status_code=500, detail="ElevenLabs API Key is invalid or missing.")
        if "QuotaExceeded" in str(e):
             raise HTTPException(status_code=500, detail="ElevenLabs quota exceeded.")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

@app.post("/api/generate/visuals")
async def generate_visuals(req: VisualsRequest, background_tasks: BackgroundTasks):
    """
    Initiates background generation of images (Title, Scenes, Entities).
    Returns a list of expected image URLs immediately for the frontend to poll.
    """
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="Analyze book first")
        
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
        
        # Return relative paths for frontend immediately
        image_urls = [f"/api/assets/visuals/{img}" for img in expected_images]
        return {"images": image_urls, "status": "generating"}
    except Exception as e:
        print(f"Visuals generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate visuals: {str(e)}")

@app.get("/api/entity_image/{name}")
async def get_entity_image(name: str, role: str = "Character", regenerate: bool = False):
    """
    Retrieves or generates an avatar image for a specific entity.
    Supports caching and regeneration.
    """
    # Check cache unless regenerating
    if not regenerate and name in state.entity_images:
        return {"image_url": f"/api/assets/entities/{os.path.basename(state.entity_images[name])}"}
        
    try:
        img_dir = os.path.join(UPLOAD_DIR, "entities")
        os.makedirs(img_dir, exist_ok=True)
        
        # If regenerating, maybe use a new seed or just re-call
        seed = None if regenerate else 42
        
        # Get style from request or default
        style = "storybook" # Default for now, could be passed in request
        
        img_path = await generate_entity_image(name, role, img_dir, seed=seed, style=style)
        
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
    """
    Answers a question about the book using the full text context.
    """
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
    
    try:
        answer = ask_question(state.full_text, req.question)
        return {"answer": answer}
    except Exception as e:
        print(f"QA Error: {e}")
        raise HTTPException(status_code=500, detail=f"QA failed: {str(e)}")

@app.get("/api/suggested_questions")
async def suggested_questions_endpoint():
    """
    Generates suggested questions based on the book's content.
    """
    if not state.full_text:
        return {"questions": []}
        
    try:
        questions = suggest_questions(state.full_text)
        return {"questions": questions}
    except Exception as e:
        print(f"Suggested questions error: {e}")
        return {"questions": []}

# Serve Static Assets (Uploaded/Generated)
app.mount("/api/assets", StaticFiles(directory=UPLOAD_DIR), name="assets")

# Serve Frontend
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Server starting... Open your browser at http://localhost:{port}")
    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)

