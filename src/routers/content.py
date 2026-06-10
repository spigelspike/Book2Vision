"""Content router — story, Q&A, podcast, storybook, download for Book2Vision API."""

import os
import time
import zipfile
import traceback
from typing import Optional, Dict
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
        "images": state.images_list,
        "latest_overview_url": state.latest_overview_url
    }


@router.get("/chapters")
async def get_chapters_endpoint():
    if not state.book_id:
        return {"chapters": []}
    
    try:
        chapters = library_manager.get_chapters(state.book_id)
        return {"chapters": chapters}
    except Exception as e:
        print(f"Error fetching chapters: {e}")
        return {"chapters": []}


# ============================================================================
# Q&A / CHAT
# ============================================================================

@router.post("/qa")
async def qa_endpoint(req: QARequest):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
    
    try:
        # Use digest for better coverage of the full book
        context = state.book_digest if state.book_digest else state.full_text
        answer = await ask_question(context, req.question)
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
        context = state.book_digest if state.book_digest else state.full_text
        questions = await suggest_questions(context)
        return {"questions": questions}
    except Exception as e:
        print(f"Suggested questions error: {e}")
        return {"questions": []}


# ============================================================================
# PODCAST
# ============================================================================

async def generate_podcast_task(podcast_text: str, book_id: Optional[int], analysis_result: Optional[Dict]):
    """Background task for podcast generation."""
    state.podcast_status = "generating"
    state.podcast_error = ""
    try:
        print("=" * 50)
        print("--- PODCAST GENERATION STARTED (Background) ---")
        print(f"Book text length: {len(podcast_text)} chars")
        print("=" * 50)
        
        # 1. Generate Script
        state.podcast_status = "scripting"
        print("--- Step 1: Generating script... ---")
        from src.podcast import generate_podcast_script, generate_podcast_audio
        script = await generate_podcast_script(podcast_text)
        
        # Check if script is error fallback
        is_error_fallback = (
            len(script) == 5 and 
            any("trouble on our end" in seg.get("text", "") or 
                "hiccup on our end" in seg.get("text", "") for seg in script)
        )
        
        if is_error_fallback:
            print("WARNING: Using fallback script due to generation failure.")
        
        print(f"SUCCESS: Script generated: {len(script)} segments")
        
        # 2. Generate Audio
        state.podcast_status = "audio"
        print("--- Step 2: Generating audio... ---")
        podcast_dir = os.path.join(UPLOAD_DIR, "podcast")
        audio_files = await generate_podcast_audio(script, podcast_dir)
        
        if not audio_files:
            state.podcast_status = "error"
            state.podcast_error = "Audio generation failed"
            print("ERROR: Audio generation failed - no files created")
            return
        
        print(f"SUCCESS: Audio generated: {len(audio_files)} files")
        
        # 3. Combine audio segments and prepare playlist
        playlist = []
        from src.storage import upload_file_to_supabase
        from moviepy import AudioFileClip, concatenate_audioclips
        
        try:
            print("--- Step 3: Combining audio segments... ---")
            clips = []
            current_time = 0.0
            
            for i, filename in enumerate(audio_files):
                local_path = os.path.join(podcast_dir, filename)
                clip = AudioFileClip(local_path)
                clips.append(clip)
                
                if i < len(script):
                    speaker = script[i]["speaker"]
                    playlist.append({
                        "speaker": speaker,
                        "text": script[i]["text"],
                        "start": current_time,
                        "end": current_time + clip.duration
                    })
                current_time += clip.duration
                
            # Combine all clips
            combined_clip = concatenate_audioclips(clips)
            
            # Determine book title for filename
            safe_title = "Unknown_Book"
            if state.ingestion_result:
                title = state.ingestion_result.get("title", state.ingestion_result.get("filename", "Unknown"))
                safe_title = "".join([c if c.isalnum() else "_" for c in title])[:30]
            
            combined_filename = f"podcast_{book_id}_{safe_title}.mp3" if book_id else f"podcast_{safe_title}.mp3"
            combined_path = os.path.join(podcast_dir, combined_filename)
            
            # Write out combined file
            combined_clip.write_audiofile(combined_path, logger=None)
            
            # Close clips to free resources
            for clip in clips:
                clip.close()
            combined_clip.close()
            
            # Upload combined file to Supabase
            print(f"--- Step 4: Uploading combined podcast {combined_filename}... ---")
            remote_filename = f"podcast/{combined_filename}"
            podcast_url = upload_file_to_supabase("media", combined_path, remote_filename)
            if podcast_url:
                print(f"--- SUCCESS: Podcast uploaded to {podcast_url} ---")
                
                # Inject URL into the first segment so the frontend can play it
                if playlist:
                    playlist[0]["url"] = podcast_url
            else:
                print(f"WARNING: Failed to upload combined podcast to Supabase")
                # Fallback to local server path
                local_url = f"/api/assets/podcast/{combined_filename}"
                if playlist:
                    playlist[0]["url"] = local_url
                
        except Exception as e:
            print(f"ERROR combining podcast audio: {e}")
            import traceback
            traceback.print_exc()
            state.podcast_status = "error"
            state.podcast_error = f"Audio combination failed: {str(e)}"
            return
        
        # Save to library
        if book_id:
            from src.state import library_manager
            library_manager.save_podcast(book_id, playlist)
        
        # Update global state
        state.podcast_playlist = playlist
        state.podcast_status = "ready"
        
        if analysis_result is not None:
            analysis_result["podcast"] = playlist
            
        print("=" * 50)
        print("--- PODCAST GENERATION COMPLETE ---")
        
    except Exception as e:
        state.podcast_status = "error"
        state.podcast_error = str(e)
        print("=" * 50)
        print(f"ERROR: PODCAST GENERATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 50)

@router.post("/generate/podcast")
async def generate_podcast_endpoint(background_tasks: BackgroundTasks):
    if not state.full_text:
        raise HTTPException(status_code=400, detail="No book uploaded")
        
    podcast_text = state.book_digest if state.book_digest else state.full_text
    
    # Reset status
    state.podcast_status = "generating"
    state.podcast_playlist = []
    state.podcast_error = ""
    
    # Start background task
    background_tasks.add_task(
        generate_podcast_task, 
        podcast_text, 
        state.book_id,
        state.analysis_result
    )
    
    return {"message": "Podcast generation started in background", "status": "generating"}

@router.get("/podcast/status")
async def get_podcast_status():
    return {
        "status": state.podcast_status,
        "playlist": state.podcast_playlist,
        "error": state.podcast_error
    }


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
        
        print(f"INFO: Zipping {len(files_to_zip)} files...")
        
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

@router.get("/assets/overviews/{filename}")
async def serve_overview(filename: str):
    """Serve overview videos from the video_overview directory."""
    try:
        # Check source folder first (demo folder)
        source_path = os.path.join(UPLOAD_DIR, "video_overview", filename)
        if os.path.exists(source_path):
            return FileResponse(source_path, media_type="video/mp4")
        
        # Check output folder (generated folder)
        book_id = state.ingestion_result.get("book_id", "latest") if state.ingestion_result else "latest"
        output_path = os.path.join(os.path.dirname(UPLOAD_DIR), "Book2Vision_Output", book_id, "overviews", filename)
        if os.path.exists(output_path):
            return FileResponse(output_path, media_type="video/mp4")
            
        raise HTTPException(status_code=404, detail="Overview video not found")
    except Exception as e:
        print(f"Overview serve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
