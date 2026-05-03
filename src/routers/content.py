"""Content router — story, Q&A, podcast, storybook, download for Book2Vision API."""

import os
import time
import zipfile
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from src.state import state, UPLOAD_DIR, library_manager
from src.models import QARequest, StorybookConfig
from src.knowledge import ask_question, suggest_questions
from src.podcast import generate_podcast_script, generate_podcast_audio
from src.storybook import generate_full_storybook, world_bible_to_json, pages_to_json

router = APIRouter(prefix="/api", tags=["content"])


# ============================================================================
# STORY
# ============================================================================

@router.get("/story")
async def get_story():
    if not state.ingestion_result:
        raise HTTPException(status_code=404, detail="No book uploaded")
    
    return {
        "body": state.ingestion_result.get("body", ""),
        "entities": state.analysis_result.get("entities", []) if state.analysis_result else [],
        "scenes": state.analysis_result.get("scenes", []) if state.analysis_result else [],
        "images": state.images_list
    }


# ============================================================================
# Q&A / CHAT
# ============================================================================

@router.post("/qa")
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


@router.get("/suggested_questions")
async def suggested_questions_endpoint():
    if not state.full_text:
        return {"questions": []}
        
    try:
        questions = suggest_questions(state.full_text)
        return {"questions": questions}
    except Exception as e:
        print(f"Suggested questions error: {e}")
        return {"questions": []}


# ============================================================================
# PODCAST
# ============================================================================

@router.post("/generate/podcast")
async def generate_podcast_endpoint(background_tasks: BackgroundTasks):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
        
    try:
        print("=" * 50)
        print("🎙️  PODCAST GENERATION STARTED")
        print(f"Book text length: {len(state.full_text)} characters")
        print("=" * 50)
        
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
            for seg in script:
                text = seg.get("text", "")
                if "Error:" in text:
                    error_msg += text
                    break
            print(f"⚠️  {error_msg}")
        
        print(f"✅ Script generated: {len(script)} segments")
        
        # 2. Generate Audio
        print("🎵 Step 2: Generating audio...")
        podcast_dir = os.path.join(UPLOAD_DIR, "podcast")
        audio_files = await generate_podcast_audio(script, podcast_dir)
        
        if not audio_files:
            raise HTTPException(status_code=500, detail="Audio generation failed - no files created")
        
        print(f"✅ Audio generated: {len(audio_files)} files")
        
        # 3. Return playlist
        playlist = []
        for i, filename in enumerate(audio_files):
            if i < len(script):
                speaker = script[i]["speaker"]
                playlist.append({
                    "speaker": speaker,
                    "text": script[i]["text"],
                    "url": f"/api/assets/podcast/{filename}"
                })
        
        print("=" * 50)
        print(f"✅ PODCAST GENERATION COMPLETE: {len(playlist)} segments")
        print("=" * 50)
        
        # Save to library
        if state.book_id:
            library_manager.save_podcast(state.book_id, playlist)
            if state.analysis_result:
                state.analysis_result["podcast"] = playlist
            
        return {"playlist": playlist}
    except HTTPException:
        raise
    except Exception as e:
        print("=" * 50)
        print("❌ PODCAST GENERATION ERROR")
        print(f"Error: {e}")
        traceback.print_exc()
        print("=" * 50)
        
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


# ============================================================================
# STORYBOOK
# ============================================================================

@router.post("/storybook/generate")
async def generate_storybook_api(config: StorybookConfig = None):
    """Generate a complete 2D illustrated storybook from the loaded book."""
    try:
        if not state.ingestion_result:
            raise HTTPException(status_code=400, detail="No book loaded")
        
        book_text = state.ingestion_result.get("raw_text", "")
        if not book_text:
            raise HTTPException(status_code=400, detail="No book text available")
        
        book_id = state.ingestion_result.get("book_id", "storybook")
        output_dir = os.path.join(UPLOAD_DIR, "storybook", book_id)
        os.makedirs(output_dir, exist_ok=True)
        
        existing_entities = state.ingestion_result.get("entities", [])
        
        world_config = {}
        if config:
            world_config = {
                "genre": config.genre,
                "age_range": config.age_range,
                "art_style": config.art_style,
                "color_palette": config.color_palette
            }
        
        provider = config.provider if config else "pollinations"
        max_pages = config.max_pages if config else 10
        
        world, pages = await generate_full_storybook(
            book_text=book_text,
            output_dir=output_dir,
            world_config=world_config,
            existing_entities=existing_entities,
            provider=provider,
            max_pages=max_pages
        )
        
        return {
            "success": True,
            "world_bible": world_bible_to_json(world),
            "pages": pages_to_json(pages),
            "total_pages": len(pages),
            "successful_pages": sum(1 for p in pages if p.image_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Storybook generation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storybook/page/{page_num}")
async def get_storybook_page(page_num: int):
    """Get a specific storybook page image."""
    try:
        if not state.ingestion_result:
            raise HTTPException(status_code=404, detail="No book loaded")
        
        book_id = state.ingestion_result.get("book_id", "storybook")
        image_path = os.path.join(UPLOAD_DIR, "storybook", book_id, f"storybook_page_{page_num:02d}.jpg")
        
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Page {page_num} not found")
        
        return FileResponse(image_path, media_type="image/jpeg")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOWNLOAD & ASSETS
# ============================================================================

@router.get("/download_all")
async def download_all_content():
    if not state.ingestion_result:
        raise HTTPException(status_code=400, detail="No book loaded")
        
    try:
        timestamp = int(time.time())
        zip_filename = f"book2vision_content_{timestamp}.zip"
        zip_path = os.path.join(UPLOAD_DIR, zip_filename)
        
        files_to_zip = []
        
        # 1. Images
        if state.images_list:
            files_to_zip.extend(state.images_list)
            
        # 2. Entity Images
        if state.entity_images:
            files_to_zip.extend(state.entity_images.values())
            
        # 3. Audiobook
        if state.audiobook_path and os.path.exists(state.audiobook_path):
            files_to_zip.append(state.audiobook_path)
            
        # 4. Podcast
        if state.analysis_result and state.analysis_result.get("podcast"):
            podcast = state.analysis_result.get("podcast")
            for seg in podcast:
                url = seg.get("url", "")
                if url:
                    filename = os.path.basename(url)
                    path = os.path.join(UPLOAD_DIR, "podcast", filename)
                    if os.path.exists(path):
                        files_to_zip.append(path)
                        
        # 5. Immersive Audio
        if state.immersive_audio_paths:
            for path in state.immersive_audio_paths:
                if os.path.exists(path):
                    files_to_zip.append(path)
        
        # 6. Cover/Poster
        if state.book_id:
            book = library_manager.get_book(state.book_id)
            if book and book.get("thumbnail"):
                thumb_path = os.path.join(UPLOAD_DIR, book["thumbnail"])
                if os.path.exists(thumb_path):
                    files_to_zip.append(thumb_path)

        if not files_to_zip:
            raise HTTPException(status_code=404, detail="No content generated yet")
            
        # Deduplicate
        files_to_zip = list(set(files_to_zip))
        
        print(f"📦 Zipping {len(files_to_zip)} files...")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in files_to_zip:
                if os.path.exists(file_path):
                    arcname = os.path.relpath(file_path, UPLOAD_DIR)
                    zipf.write(file_path, arcname)
                    
        return FileResponse(zip_path, filename=zip_filename, media_type='application/zip')
        
    except Exception as e:
        print(f"Download error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to create download package")


# Serve video assets from OUTPUT_DIR
@router.get("/assets/videos/{filename}")
async def serve_video(filename: str):
    """Serve video files from the latest book's videos directory"""
    from src.state import OUTPUT_DIR
    try:
        if not state.ingestion_result:
            raise HTTPException(status_code=404, detail="No book loaded")
        
        book_id = state.ingestion_result.get("book_id", "latest")
        video_path = os.path.join(OUTPUT_DIR, book_id, "videos", filename)
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video not found")
        
        return FileResponse(video_path, media_type="video/mp4")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Video serve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
