"""Generation router — audio, visuals, portraits, video for Book2Vision API."""

import os
import shutil
import time
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse

from src.state import state, UPLOAD_DIR, OUTPUT_DIR, library_manager
from src.models import (
    AudioRequest, VisualsRequest, ImmersiveAudioRequest,
    CharacterPortraitsRequest, VideoRequest
)
from src.audio import generate_audio as generate_audio_service
from src.visuals import (
    generate_images, generate_entity_image, generate_poster_with_deapi
)
from src.video import generate_video_with_deapi

router = APIRouter(prefix="/api", tags=["generation"])


# ============================================================================
# AUDIO
# ============================================================================

@router.post("/generate/audio")
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
        
        # Get title and author for audiobook intro
        title = None
        author = None
        if state.ingestion_result:
            title = state.ingestion_result.get("title")
            author = state.ingestion_result.get("author")
            
        audio_file = await generate_audio_service(
            preview_text, 
            output_path, 
            voice_id=req.voice_id,
            stability=req.stability,
            similarity_boost=req.similarity_boost,
            style=req.style,
            use_speaker_boost=req.use_speaker_boost,
            provider=req.provider,
            title=title,
            author=author
        )
        
        if not audio_file:
             print("ERROR: generate_audio_service returned None")
             raise HTTPException(status_code=500, detail="Audio generation failed. Check server logs.")
        
        print(f"Audio file created: {audio_file}")
        state.audiobook_path = audio_file  # Track for download
        return {"audio_url": f"/api/assets/{filename}"}
    except HTTPException:
        raise
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"=== AUDIO GENERATION ERROR ===")
        print(error_details)
        
        provider = req.provider
        
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


@router.post("/upload-voice-sample")
async def upload_voice_sample(voice_sample: UploadFile = File(...)):
    """Upload a voice sample for the Colab Voice Clone provider."""
    try:
        # Validate format
        if not voice_sample.filename.lower().endswith('.wav'):
             raise HTTPException(status_code=400, detail="Only .wav files are supported for voice cloning currently.")
             
        # Create directory if it doesn't exist
        samples_dir = os.path.join(UPLOAD_DIR, "voice_samples")
        os.makedirs(samples_dir, exist_ok=True)
        
        # Save file
        timestamp = int(time.time())
        filename = f"sample_{timestamp}.wav"
        filepath = os.path.join(samples_dir, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(voice_sample.file, buffer)
            
        # Update state
        state.voice_sample_path = filepath
        
        return {"message": "Voice sample uploaded successfully", "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading voice sample: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload voice sample.")


from pydantic import BaseModel
class ColabUrlRequest(BaseModel):
    url: str

@router.post("/set-colab-url")
async def set_colab_url(req: ColabUrlRequest):
    """Set the ngrok URL for the Colab Voice Clone provider."""
    state.colab_url = req.url
    print(f"Colab URL set to: {req.url}")
    return {"message": "Colab URL saved successfully."}

# ============================================================================
# VISUALS
# ============================================================================

@router.post("/generate/visuals")
async def generate_visuals(req: VisualsRequest, background_tasks: BackgroundTasks):
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="Analyze book first")
    
    # Add validation
    if not state.analysis_result.get("scenes") and not state.analysis_result.get("entities"):
        raise HTTPException(status_code=400, detail="Analysis did not produce scenes or entities for visualization")
    
    # Ensure minimum scenes (fixes issue with old analyses having few scenes)
    from src.analysis import ensure_minimum_scenes
    ensure_minimum_scenes(state.analysis_result)

        
    try:
        visuals_dir = os.path.join(UPLOAD_DIR, "visuals")
        os.makedirs(visuals_dir, exist_ok=True)
        
        # Clean directory but PRESERVE COVERS
        for filename in os.listdir(visuals_dir):
            if filename.startswith("cover_"):
                continue  # Skip covers
            
            file_path = os.path.join(visuals_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
        
        # Get title - prefer filename if title is generic
        title = state.ingestion_result.get("title", "Unknown") if state.ingestion_result else "Book"
        if title in ["Unknown", "Extracted PDF", "Book"] and state.ingestion_result and state.ingestion_result.get("filename"):
             title = state.ingestion_result.get("filename")
        
        # Prepare list of expected images so frontend knows what to wait for
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
        
        print("=" * 50)
        print(f"🎨 VISUALS GENERATION REQUESTED")
        print(f"Style: {req.style}")
        print(f"Expected Images: {len(expected_images)}")
        print("=" * 50)
        
        # Start background generation
        background_tasks.add_task(
            generate_images, 
            state.analysis_result, 
            visuals_dir, 
            style=req.style, 
            seed=req.seed, 
            title=title, 
            include_entities=True
        )
        
        # Update thumbnail in library
        if state.book_id:
            current_book = library_manager.get_book(state.book_id)
            has_cover = current_book and (current_book.get("thumbnail") or "").startswith("visuals/cover_")
            
            if not has_cover:
                thumbnail_filename = None
                scenes = state.analysis_result.get("scenes", [])
                if len(scenes) > 0:
                     thumbnail_filename = f"image_01_scene_01.jpg"
                elif len(expected_images) > 0:
                     thumbnail_filename = expected_images[0]
                
                if thumbnail_filename:
                    library_manager.update_book_thumbnail(state.book_id, f"visuals/{thumbnail_filename}")

        # Return relative paths for frontend immediately
        image_urls = [f"/api/assets/visuals/{img}" for img in expected_images]
        print(f"✅ Returning {len(image_urls)} expected images to frontend: {image_urls}")
        return {"images": image_urls, "status": "generating"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Visuals generation error: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate visuals. Please try again.")


@router.post("/generate/poster")
async def generate_poster(background_tasks: BackgroundTasks):
    if not state.book_id:
        raise HTTPException(status_code=400, detail="No book loaded")
    
    try:
        visuals_dir = os.path.join(UPLOAD_DIR, "visuals")
        os.makedirs(visuals_dir, exist_ok=True)
        
        # Get metadata
        book = library_manager.get_book(state.book_id)
        if not book:
             raise HTTPException(status_code=404, detail="Book not found")
             
        title = book.get("title", "Unknown Book")
        author = book.get("author", "Unknown Author")
        
        # Extract context from state if available
        theme = ""
        characters = []
        if state.analysis_result:
            characters = state.analysis_result.get("entities", [])
        
        poster_path = await generate_poster_with_deapi(title, author, visuals_dir, theme=theme, characters=characters)
        
        if poster_path:
            filename = os.path.basename(poster_path)
            library_manager.update_book_thumbnail(state.book_id, f"visuals/{filename}")
            
            return {
                "poster_url": f"/api/assets/visuals/{filename}",
                "message": "Poster generated successfully"
            }
        else:
             raise HTTPException(status_code=500, detail="Failed to generate poster")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Poster generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity_image/{name}")
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


# ============================================================================
# CHARACTER PORTRAITS
# ============================================================================

@router.post("/generate/character-portraits")
async def generate_character_portraits_endpoint(req: CharacterPortraitsRequest, background_tasks: BackgroundTasks):
    """Generate consistent character portraits for all detected characters."""
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="Analyze book first")
    
    entities = state.analysis_result.get("entities", [])
    if not entities:
        raise HTTPException(status_code=400, detail="No characters detected for portrait generation")
    
    try:
        from src.visuals import generate_all_character_portraits
        
        portraits_dir = os.path.join(UPLOAD_DIR, "portraits")
        os.makedirs(portraits_dir, exist_ok=True)
        
        # Prepare expected filenames for immediate response
        expected_portraits = []
        for entity in entities:
            if isinstance(entity, list) and len(entity) >= 1:
                name = entity[0]
            else:
                continue
            safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
            expected_portraits.append(f"portrait_{safe_name}.jpg")
        
        print(f"🎭 Generating {len(expected_portraits)} character portraits...")
        
        # Run in background
        background_tasks.add_task(
            generate_all_character_portraits,
            state.analysis_result,
            portraits_dir,
            style=req.style,
            genre=req.genre
        )
        
        # Return URLs immediately (images will be generated in background)
        portrait_urls = [f"/api/assets/portraits/{img}" for img in expected_portraits]
        return {
            "portraits": portrait_urls,
            "status": "generating",
            "count": len(expected_portraits)
        }
    except Exception as e:
        print(f"Character portraits error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate character portraits")


@router.get("/character/{name}/portrait")
async def get_character_portrait(name: str, style: str = "anime", genre: str = "fantasy"):
    """Get or generate a single character portrait."""
    # Look for existing portrait
    portraits_dir = os.path.join(UPLOAD_DIR, "portraits")
    safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
    portrait_path = os.path.join(portraits_dir, f"portrait_{safe_name}.jpg")
    
    if os.path.exists(portrait_path):
        return {"portrait_url": f"/api/assets/portraits/portrait_{safe_name}.jpg?t={int(time.time())}"}
    
    # Find character in analysis to get details
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="No book analyzed")
    
    entities = state.analysis_result.get("entities", [])
    character = None
    for entity in entities:
        if isinstance(entity, list) and len(entity) >= 1 and entity[0].lower() == name.lower():
            character = entity
            break
    
    if not character:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")
    
    try:
        from src.visuals import generate_character_portrait
        
        os.makedirs(portraits_dir, exist_ok=True)
        
        # Parse character data
        if len(character) >= 5:
            char_name, role, physical, outfit, prop = character[0], character[1], character[2], character[3], character[4]
        elif len(character) >= 3:
            char_name, role, physical = character[0], character[1], character[2]
            outfit = "appropriate attire"
            prop = "none"
        else:
            char_name, role = character[0], character[1] if len(character) > 1 else "Character"
            physical = "distinctive appearance"
            outfit = "appropriate attire"
            prop = "none"
        
        result = await generate_character_portrait(
            name=char_name,
            role=role,
            physical_description=physical,
            outfit=outfit,
            signature_prop=prop,
            output_dir=portraits_dir,
            style=style,
            genre=genre
        )
        
        if result:
            return {"portrait_url": f"/api/assets/portraits/portrait_{safe_name}.jpg?t={int(time.time())}"}
        else:
            raise HTTPException(status_code=500, detail="Portrait generation failed")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Single portrait error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/character/{name}/sheet")
async def get_character_sheet(name: str, style: str = "anime"):
    """Get or generate a character reference sheet."""
    portraits_dir = os.path.join(UPLOAD_DIR, "portraits")
    safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
    sheet_path = os.path.join(portraits_dir, f"sheet_{safe_name}.jpg")
    
    if os.path.exists(sheet_path):
        return {"sheet_url": f"/api/assets/portraits/sheet_{safe_name}.jpg?t={int(time.time())}"}
    
    # Find character
    if not state.analysis_result:
        raise HTTPException(status_code=400, detail="No book analyzed")
    
    entities = state.analysis_result.get("entities", [])
    character = None
    for entity in entities:
        if isinstance(entity, list) and len(entity) >= 1 and entity[0].lower() == name.lower():
            character = entity
            break
    
    if not character:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")
    
    try:
        from src.visuals import generate_character_sheet
        
        os.makedirs(portraits_dir, exist_ok=True)
        
        # Parse character data
        if len(character) >= 5:
            char_name, role, physical, outfit, prop = character[0], character[1], character[2], character[3], character[4]
        elif len(character) >= 3:
            char_name, role, physical = character[0], character[1], character[2]
            outfit = "appropriate attire"
            prop = "none"
        else:
            char_name, role = character[0], character[1] if len(character) > 1 else "Character"
            physical = "distinctive appearance"
            outfit = "appropriate attire"
            prop = "none"
        
        result = await generate_character_sheet(
            name=char_name,
            role=role,
            physical_description=physical,
            outfit=outfit,
            signature_prop=prop,
            output_dir=portraits_dir,
            style=style
        )
        
        if result:
            return {"sheet_url": f"/api/assets/portraits/sheet_{safe_name}.jpg?t={int(time.time())}"}
        else:
            raise HTTPException(status_code=500, detail="Sheet generation failed")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Character sheet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve portrait assets
@router.get("/assets/portraits/{filename}")
async def serve_portrait(filename: str):
    """Serve portrait files."""
    # Validate filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(UPLOAD_DIR, "portraits", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Portrait not found")
    
    return FileResponse(file_path, media_type="image/jpeg")


# ============================================================================
# IMMERSIVE AUDIO
# ============================================================================

async def generate_scene_audios(scenes, output_dir, voice_id, provider):
    """Helper to generate audio for all scenes sequentially."""
    for i, scene in enumerate(scenes):
        try:
            # Handle both dict and string formats
            if isinstance(scene, dict):
                text = f"{scene.get('narrator_intro', '')} {scene.get('excerpt', '')}".strip()
                if not text:
                    text = scene.get('description', '')  # Fallback
            else:
                text = str(scene)
            
            filename = f"immersive_scene_{i+1:02d}.mp3"
            output_path = os.path.join(output_dir, filename)
            
            print(f"Generating immersive audio for scene {i+1}...")
            await generate_audio_service(
                text, 
                output_path, 
                voice_id=voice_id,
                provider=provider
            )
        except Exception as e:
            print(f"Failed to generate audio for scene {i+1}: {e}")


@router.post("/generate/immersive_audio")
async def generate_immersive_audio(req: ImmersiveAudioRequest, background_tasks: BackgroundTasks):
    if not state.analysis_result or not state.analysis_result.get("scenes"):
        raise HTTPException(status_code=400, detail="No scenes available. Analyze book first.")
        
    try:
        immersive_dir = os.path.join(UPLOAD_DIR, "immersive_audio")
        os.makedirs(immersive_dir, exist_ok=True)
        
        scenes = state.analysis_result.get("scenes", [])
        expected_audio = []
        
        for i in range(len(scenes)):
            filename = f"immersive_scene_{i+1:02d}.mp3"
            expected_audio.append(f"/api/assets/immersive_audio/{filename}")
            
        # Start background generation
        background_tasks.add_task(
            generate_scene_audios, 
            scenes, 
            immersive_dir, 
            req.voice_id, 
            req.provider
        )
        
        # Track expected paths for download
        state.immersive_audio_paths = [os.path.join(immersive_dir, os.path.basename(url)) for url in expected_audio]
        
        return {"audio_urls": expected_audio, "status": "generating"}
    except Exception as e:
        print(f"Immersive audio error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VIDEO
# ============================================================================

@router.post("/generate/scene_video")
async def generate_scene_video(req: VideoRequest):
    """Generate video from a scene image using DepAI"""
    try:
        # Find the image file
        images_dir = os.path.join(OUTPUT_DIR, state.ingestion_result.get("book_id", "latest"), "images")
        image_path = os.path.join(images_dir, req.image_filename)
        
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image not found: {req.image_filename}")
        
        # Create videos directory
        videos_dir = os.path.join(OUTPUT_DIR, state.ingestion_result.get("book_id", "latest"), "videos")
        os.makedirs(videos_dir, exist_ok=True)
        
        # Generate video
        video_path = await generate_video_with_deapi(
            image_path=image_path,
            prompt=req.prompt or "Animate this scene with subtle movements",
            output_dir=videos_dir,
            duration=req.duration
        )
        
        if not video_path:
            raise HTTPException(status_code=500, detail="Video generation failed")
        
        video_filename = os.path.basename(video_path)
        video_url = f"/api/assets/videos/{video_filename}"
        
        return {"video_url": video_url, "status": "complete"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Video generation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
