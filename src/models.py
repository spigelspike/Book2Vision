"""Pydantic request/response models for Book2Vision API."""

from pydantic import BaseModel
from typing import Optional


class AudioRequest(BaseModel):
    text: str
    voice_id: str = "pNInz6obpgDQGcFmaJgB"  # Adam (deep voice)
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    provider: str = "elevenlabs"  # elevenlabs, deepgram, inbuilt, voice_clone
    voice_sample: Optional[str] = None
    colab_url: Optional[str] = None


class VisualsRequest(BaseModel):
    style: str = "storybook"
    seed: int = 42


class QARequest(BaseModel):
    question: str


class ImmersiveAudioRequest(BaseModel):
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    provider: str = "deepgram"


class CharacterPortraitsRequest(BaseModel):
    style: str = "anime"
    genre: str = "fantasy"


class VideoRequest(BaseModel):
    image_filename: str
    prompt: str = ""
    duration: int = 5


class StorybookConfig(BaseModel):
    """Configuration for storybook generation."""
    genre: Optional[str] = "children's fantasy"
    age_range: Optional[str] = "4-8 years"
    art_style: Optional[str] = "watercolor illustration"
    color_palette: Optional[str] = "warm, soft pastels"
    max_pages: Optional[int] = 10
    provider: Optional[str] = "pollinations"  # pollinations or deapi
