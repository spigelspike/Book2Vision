import aiohttp
import asyncio
import os
import random
import time
import requests
from typing import List, Optional

async def generate_video_with_deapi(image_path, prompt, output_dir, duration=5, model="SVD"):
    """
    Generates a video from an image using DepAI's img2vid endpoint.
    
    Args:
        image_path: Path to the source image
        prompt: Text prompt to guide the animation
        output_dir: Directory to save the video
        duration: Video duration in seconds (default 5)
        model: The model to use (SVD, LTX-2-19B, etc.)
        
    Returns:
        Path to the generated video file or None on failure
    """
    api_key = os.getenv("DEAPI_API_KEY")
    if not api_key:
        print(" DEAPI_API_KEY not found for video generation.")
        return None
    
    try:
        # Read the image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Prepare the request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        
        # Create form data
        form_data = aiohttp.FormData()
        form_data.add_field('image', image_data, filename=os.path.basename(image_path), content_type='image/jpeg')
        form_data.add_field('prompt', prompt)
        form_data.add_field('duration', str(duration))
        form_data.add_field('model', model)
        
        # LTX-2 specific enhancements if requested
        if "LTX" in model:
            form_data.add_field('fps', '24')
            form_data.add_field('resolution', '1024x1024')
        
        print(f" Requesting video generation from DepAI using model: {model}...")
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Submit the request
            async with session.post(
                "https://api.deapi.ai/api/v1/client/img2vid",
                headers=headers,
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f" DepAI video request failed: {response.status}")
                    print(f"Response: {error_text}")
                    return None
                
                data = await response.json()
                request_id = data.get("data", {}).get("request_id")
                
                if not request_id:
                    print(" No request_id in DepAI response")
                    return None
                
                print(f" Video request ID: {request_id}")
            
            # Step 2: Poll for completion
            # Video generation is slow, so we poll for up to 10 minutes for LTX-2
            max_attempts = 300 if "LTX" in model else 60 
            poll_interval = 2
            result_url = None
            
            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)
                
                async with session.get(
                    f"https://api.deapi.ai/api/v1/client/request-status/{request_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as status_response:
                    if status_response.status != 200:
                        continue
                    
                    status_data = await status_response.json()
                    status = status_data.get("data", {}).get("status")
                    result_url = status_data.get("data", {}).get("result_url") or status_data.get("data", {}).get("result")
                    
                    if status in ["completed", "done"] and result_url:
                        print(f" Video generation complete!")
                        break
                    elif status == "failed":
                        print(f" DepAI video generation failed")
                        return None
                    
                    if attempt % 10 == 0:
                        print(f" Waiting for video... ({attempt * poll_interval}s elapsed)")
            
            if not result_url:
                print(" Video generation timed out")
                return None
            
            # Step 3: Download the video
            print(f" Downloading video from: {result_url}")
            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=120)) as video_response:
                if video_response.status != 200:
                    print(f" Failed to download video: {video_response.status}")
                    return None
                
                video_data = await video_response.read()
                
                # Save the video
                filename = f"video_{model.lower()}_{os.path.basename(image_path)}.mp4"
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(video_data)
                
                print(f" Video saved: {output_path}")
                return output_path
    
    except Exception as e:
        print(f" DepAI video generation error: {e}")
        return None

async def combine_videos_with_audio(video_paths: List[str], audio_path: str, output_path: str):
    """
    Combines multiple video segments and overlays an audio track using MoviePy.
    """
    try:
        from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip
        
        print(f" Combining {len(video_paths)} videos with audio: {audio_path}")
        
        clips = []
        for path in video_paths:
            if os.path.exists(path):
                clips.append(VideoFileClip(path))
        
        if not clips:
            print(" No valid video clips to combine")
            return None
            
        # Concatenate videos
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Load audio
        if os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            
            # If video is shorter than audio, loop video or just cut audio
            # For "Overview", we usually cut audio to video length or vice versa
            # Let's match audio to video length for now
            if audio_clip.duration > final_video.duration:
                audio_clip = audio_clip.subclipped(0, final_video.duration)
            
            final_video = final_video.with_audio(audio_clip)
        
        # Write final file
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        # Close clips to free memory
        for clip in clips:
            clip.close()
        if 'audio_clip' in locals():
            audio_clip.close()
        final_video.close()
        
        return output_path
    except Exception as e:
        print(f" Video combination error: {e}")
        return None
