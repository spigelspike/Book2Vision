import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion import ingest_book, clean_format
from src.analysis import semantic_analysis
from src.audio import generate_audiobook, generate_audio as generate_audio_service
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
    # Validate critical env vars
    if not os.getenv("GEMINI_API_KEY"):
        print("CRITICAL WARNING: GEMINI_API_KEY is not set. AI features will fail.")
    else:
        print("GEMINI_API_KEY found.")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "book2vision"}

# Directories
UPLOAD_DIR = "temp_upload"
OUTPUT_DIR = "Book2Vision_Output"
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

class VisualsRequest(BaseModel):
    style: str = "storybook"
    seed: int = 42

class QARequest(BaseModel):
    question: str

# Endpoints

@app.post("/api/upload")
async def upload_book(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest
        ingestion_result = ingest_book(file_path)
        ingestion_result["filename"] = file.filename
        
        # Store state
        state.ingestion_result = ingestion_result
        state.full_text = ingestion_result.get("full_text", "")
        
        # Analysis
        analysis = semantic_analysis(state.full_text)
        state.analysis_result = analysis
        
        # Pre-generate images for top entities (Automated)
        entities = analysis.get("entities", [])[:5]
        img_dir = os.path.join(UPLOAD_DIR, "entities")
        os.makedirs(img_dir, exist_ok=True)
        
        print(f"Pre-generating images for {len(entities)} entities...")
        for ent in entities:
            # Handle list format [name, role]
            if isinstance(ent, list) and len(ent) >= 1:
                name = ent[0]
                role = ent[1] if len(ent) > 1 else "Character"
                
                # Generate if not already cached
                if name not in state.entity_images:
                    img_path = generate_entity_image(name, role, img_dir)
                    if img_path:
                        state.entity_images[name] = img_path
        
        return {
            "message": "Upload and analysis successful",
            "filename": file.filename,
            "analysis": analysis,
            "title": ingestion_result.get("title", "Unknown"),
            "author": ingestion_result.get("author", "Unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # For demo, just use preview text
        preview_text = req.text[:2000]
        output_path = os.path.join(UPLOAD_DIR, "audiobook.mp3")
        
        print(f"Calling generate_audio_service...")
        
        audio_file = await generate_audio_service(
            preview_text, 
            output_path, 
            voice_id=req.voice_id,
            stability=req.stability,
            similarity_boost=req.similarity_boost,
            style=req.style,
            use_speaker_boost=req.use_speaker_boost
        )
        
        if not audio_file:
             print("ERROR: generate_audio_service returned None")
             raise HTTPException(status_code=500, detail="Audio generation failed")
        
        print(f"Audio file created: {audio_file}")
        return {"audio_url": f"/api/assets/audiobook.mp3"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=== AUDIO GENERATION ERROR ===")
        print(error_details)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/visuals")
async def generate_visuals(req: VisualsRequest):
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="Analyze book first")
        
    try:
        visuals_dir = os.path.join(UPLOAD_DIR, "visuals")
        os.makedirs(visuals_dir, exist_ok=True)
        
        # Get title
        title = state.ingestion_result.get("title", "Unknown") if state.ingestion_result else "Book"
        
        # Generate images
        images = generate_images(state.analysis_result, visuals_dir, style=req.style, seed=req.seed, title=title)
        state.images_list = images
        
        # Return relative paths for frontend
        image_urls = [f"/api/assets/visuals/{os.path.basename(img)}" for img in images]
        return {"images": image_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/entity_image/{name}")
async def get_entity_image(name: str, role: str = "Character"):
    # Check cache
    if name in state.entity_images:
        return {"image_url": f"/api/assets/entities/{os.path.basename(state.entity_images[name])}"}
        
    try:
        img_dir = os.path.join(UPLOAD_DIR, "entities")
        os.makedirs(img_dir, exist_ok=True)
        img_path = generate_entity_image(name, role, img_dir)
        
        if img_path:
            state.entity_images[name] = img_path
            return {"image_url": f"/api/assets/entities/{os.path.basename(img_path)}"}
        else:
            return {"image_url": None}
    except Exception as e:
        print(f"Entity image error: {e}")
        return {"image_url": None}

@app.post("/api/qa")
async def qa_endpoint(req: QARequest):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
    
    answer = ask_question(state.full_text, req.question)
    return {"answer": answer}

@app.get("/api/suggested_questions")
async def suggested_questions_endpoint():
    if not state.full_text:
        return {"questions": []}
        
    questions = suggest_questions(state.full_text)
    return {"questions": questions}

# Serve Static Assets (Uploaded/Generated)
app.mount("/api/assets", StaticFiles(directory=UPLOAD_DIR), name="assets")

# Serve Frontend
app.mount("/", StaticFiles(directory="web", html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)

