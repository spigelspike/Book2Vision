import asyncio
import requests

import google.generativeai as genai
from src.config import ELEVENLABS_API_KEY, GEMINI_API_KEY, DEEPGRAM_API_KEY
from src.prompts import SSML_PROMPT

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

async def generate_ssml(text):
    """
    Rewrites text into SSML using Gemini for natural narration.
    """
    print("Generating SSML with Gemini...")
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(SSML_PROMPT.format(text=text))
        ssml_text = response.text
        
        # Basic cleanup to ensure it's just the SSML if the model adds markdown
        if "```xml" in ssml_text:
            ssml_text = ssml_text.split("```xml")[1].split("```")[0].strip()
        elif "```" in ssml_text:
            ssml_text = ssml_text.split("```")[1].split("```")[0].strip()
            
        return ssml_text
    except Exception as e:
        print(f"Error generating SSML: {e}")
        return text # Fallback to original text

<<<<<<< HEAD
async def generate_audio_deepgram(text, output_path):
    """
    Generates audio using Deepgram API.
    """
    print(f"Generating audio using Deepgram...")
    if not DEEPGRAM_API_KEY:
        print("ERROR: DEEPGRAM_API_KEY is missing!")
        raise Exception("DEEPGRAM_API_KEY is missing!")
        
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
=======
def get_deepgram_voice(voice_id: str) -> str:
    """
    Map ElevenLabs/generic voice IDs to Deepgram Aura-2 voices.
    Uses best-quality Aura-2 models.
    """
    voice_map = {
        "pNInz6obpgDQGcFmaJgB": "aura-2-odysseus-en",  # Adam -> Odysseus (Masculine, clear for Jax)
        "21m00Tcm4TlvDq8ikWAM": "aura-2-luna-en",      # Rachel -> Luna (Feminine, friendly for Emma)
    }
    return voice_map.get(voice_id, "aura-2-odysseus-en")

async def generate_audio_deepgram(text, output_path, voice_id="21m00Tcm4TlvDq8ikWAM"):
    """
    Generates audio using Deepgram Aura-2 TTS API.
    Automatically selects appropriate voice based on voice_id mapping.
    """
    if not DEEPGRAM_API_KEY:
        print("ERROR: DEEPGRAM_API_KEY is missing!")
        raise Exception("DEEPGRAM_API_KEY is missing!")
    
    # Get the appropriate Deepgram voice
    deepgram_voice = get_deepgram_voice(voice_id)
    print(f"Generating audio using Deepgram Aura-2 ({deepgram_voice})...")
    
    url = f"https://api.deepgram.com/v1/speak?model={deepgram_voice}"
>>>>>>> temp_fix
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text
    }
    
    try:
        def make_request():
            return requests.post(url, headers=headers, json=payload)
            
        response = await asyncio.to_thread(make_request)
        
        if response.status_code == 200:
            def write_file():
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
            
            result = await asyncio.to_thread(write_file)
<<<<<<< HEAD
            print(f"Deepgram audio saved to {result}")
            return result
        else:
            error_msg = f"Deepgram Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        print(f"Deepgram failed: {e}")
        raise e

async def generate_audio(text, output_path="audiobook.mp3", voice_id="21m00Tcm4TlvDq8ikWAM", stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True, provider="elevenlabs"):
    """
    Generates audio using the specified provider.
    """
    print(f"Generating audio with provider: {provider}")
    
    # Check for keys and fallback
    if provider == "deepgram" and not DEEPGRAM_API_KEY:
        print("Deepgram key missing. Falling back to Inbuilt (Edge TTS).")
        provider = "inbuilt"
    elif provider == "elevenlabs" and not ELEVENLABS_API_KEY:
        print("ElevenLabs key missing. Falling back to Inbuilt (Edge TTS).")
        provider = "inbuilt"
    
    if provider == "deepgram":
        return await generate_audio_deepgram(text, output_path)
    elif provider == "inbuilt":
        return await generate_audio_edge(text, output_path)
    else:
        # Default to ElevenLabs
        return await generate_audio_elevenlabs(text, output_path, voice_id, stability, similarity_boost, style, use_speaker_boost)
=======
            print(f"✅ Deepgram audio saved: {result}")
            return result
        else:
            error_msg = f"Deepgram API Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        print(f"❌ Deepgram failed: {e}")
        raise e

async def generate_audio(text, output_path="audiobook.mp3", voice_id="21m00Tcm4TlvDq8ikWAM", stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True, provider="elevenlabs", speaking_rate=1.0):
    """
    Generates audio using the specified provider with automatic fallback.
    Priority: Deepgram -> Edge TTS (inbuilt)
    """
    print(f"🎵 Generating audio with provider: {provider} (Rate: {speaking_rate})")
    
    # Deepgram with automatic fallback to edge-tts
    if provider == "deepgram":
        if not DEEPGRAM_API_KEY:
            print("⚠️  Deepgram key missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        
        try:
            return await generate_audio_deepgram(text, output_path, voice_id)
        except Exception as e:
            print(f"⚠️  Deepgram failed: {e}. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
    
    # Edge TTS (inbuilt)
    elif provider == "inbuilt":
        return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
    
    # ElevenLabs with fallback
    elif provider == "elevenlabs":
        if not ELEVENLABS_API_KEY:
            print("⚠️  ElevenLabs key missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        return await generate_audio_elevenlabs(text, output_path, voice_id, stability, similarity_boost, style, use_speaker_boost)
    
    # Default fallback
    else:
        print(f"⚠️  Unknown provider '{provider}'. Using Edge TTS.")
        return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
>>>>>>> temp_fix

async def generate_audio_elevenlabs(text, output_path, voice_id, stability, similarity_boost, style, use_speaker_boost):
    """
    Generates audio using ElevenLabs API.
    """
    print(f"Generating audio for {len(text)} characters using ElevenLabs ({voice_id})...")
    if not ELEVENLABS_API_KEY:
        print("ERROR: ELEVENLABS_API_KEY is missing!")
        raise Exception("ELEVENLABS_API_KEY is missing!")
    else:
        print(f"API Key present: {bool(ELEVENLABS_API_KEY)}")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }
    }
    
    try:
        # Run the blocking requests call in a thread pool to avoid blocking the event loop
        def make_request():
            return requests.post(url, headers=headers, json=payload)
        
        response = await asyncio.to_thread(make_request)
        
        if response.status_code == 200:
            # Write file in thread pool as well
            def write_file():
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
            
            result = await asyncio.to_thread(write_file)
            print(f"Audio saved to {result}")
            return result
        else:
            error_msg = f"ElevenLabs Error: {response.status_code} - {response.text}"
            print(error_msg)
            if response.status_code == 401:
                if "missing_permissions" in response.text:
                    print("WARNING: ElevenLabs Key lacks 'text_to_speech' permission. Falling back to Edge TTS.")
                    raise Exception("ElevenLabs Key lacks 'text_to_speech' permission.")
                else:
                    raise Exception("Invalid ElevenLabs API Key.")
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Exception in ElevenLabs TTS: {e}")
        print("Falling back to Edge TTS...")
        return await generate_audio_edge(text, output_path, voice_id)

async def generate_audio_edge(text, output_path, voice_id=None, rate=1.0):
    """
    Fallback using edge-tts (free).
    """
    try:
        import edge_tts
        
        # Calculate rate string (e.g., "+10%", "-10%")
        rate_str = "+0%"
        if rate != 1.0:
            percent = int((rate - 1.0) * 100)
            sign = "+" if percent >= 0 else ""
            rate_str = f"{sign}{percent}%"
            
        print(f"Generating audio using Edge TTS (Rate: {rate_str})...")
        
        # Map ElevenLabs IDs to Edge Voices if possible, or use a default mapping
        edge_voice = "en-US-ChristopherNeural" # Default
        
        # Simple mapping for Podcast fallback
        # Adam (Jax) -> Guy
        # Rachel (Emma) -> Aria
        if "pNInz6obpgDQGcFmaJgB" in str(voice_id): # Adam ID
             edge_voice = "en-US-GuyNeural"
        elif "21m00Tcm4TlvDq8ikWAM" in str(voice_id): # Rachel ID
             edge_voice = "en-US-AriaNeural"
             
        communicate = edge_tts.Communicate(text, edge_voice, rate=rate_str)
        await communicate.save(output_path)
        print(f"Audio saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Edge TTS failed: {e}")
        raise e


