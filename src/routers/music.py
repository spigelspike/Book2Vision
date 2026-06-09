"""Music router — endpoints for ambient background music."""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from src.state import UPLOAD_DIR

router = APIRouter(prefix="/api/music", tags=["music"])

MUSIC_DIR = os.path.join(UPLOAD_DIR, "music")

@router.get("/tracks")
async def list_music():
    """List all available ambient music tracks."""
    if not os.path.exists(MUSIC_DIR):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        return {"tracks": []}
    
    tracks = []
    for f in os.listdir(MUSIC_DIR):
        if f.endswith(('.mp3', '.wav', '.m4a')):
            # Simple track ID based on filename
            track_id = f.replace(".mp3", "").replace(".wav", "").replace(".m4a", "")
            tracks.append({
                "id": track_id,
                "title": track_id.replace("_", " ").title(),
                "filename": f
            })
    return {"tracks": tracks}

@router.get("/play/{track_id}")
async def play_music(track_id: str):
    """Serve a specific music track."""
    if not os.path.exists(MUSIC_DIR):
        raise HTTPException(status_code=404, detail="Music directory not found")
        
    # Try common extensions
    for ext in ['.mp3', '.wav', '.m4a']:
        file_path = os.path.join(MUSIC_DIR, f"{track_id}{ext}")
        if os.path.exists(file_path):
            return FileResponse(file_path)
            
    raise HTTPException(status_code=404, detail="Music track not found")
