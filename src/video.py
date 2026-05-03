import aiohttp
import asyncio
import os
import random
import time

async def generate_video_with_deapi(image_path, prompt, output_dir, duration=5):
    """
    Generates a video from an image using DepAI's img2vid endpoint.
    
    Args:
        image_path: Path to the source image
        prompt: Text prompt to guide the animation
        output_dir: Directory to save the video
        duration: Video duration in seconds (default 5)
        
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
        form_data.add_field('model', 'SVD')  # Stable Video Diffusion
        
        print(f" Requesting video generation from DepAI...")
        
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
            max_attempts = 60  # 2 minutes max (2s intervals)
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
                filename = f"video_{os.path.basename(image_path)}.mp4"
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(video_data)
                
                print(f" Video saved: {output_path}")
                return output_path
    
    except Exception as e:
        print(f" DepAI video generation error: {e}")
        import traceback
        traceback.print_exc()
        return None
