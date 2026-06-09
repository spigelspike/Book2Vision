import asyncio
import requests

try:
    from google import genai
except ImportError:
    genai = None

from src.config import ELEVENLABS_API_KEY, GEMINI_API_KEYS, DEEPGRAM_API_KEY, POLLINATIONS_API_KEY, PODCAST_API_KEY
from src.prompts import SSML_PROMPT

# Configure Gemini
# genai.configure(api_key=GEMINI_API_KEY) # Not needed with new SDK client

async def generate_ssml(text, chapter_id=None):
    """
    Rewrites text into SSML using Gemini for natural narration with key rotation.
    Implements database caching to save API quota.
    """
    from src.database import Chapter, engine, Session
    from src.config import PODCAST_API_KEYS, GEMINI_API_KEYS
    
    # 1. Check Cache
    if chapter_id:
        with Session(engine) as session:
            ch = session.get(Chapter, chapter_id)
            if ch and ch.enhanced_script and "<speak>" in ch.enhanced_script:
                print(f"CACHE HIT: Using existing SSML script for chapter {chapter_id}")
                return ch.enhanced_script

    print("Generating SSML with Gemini...")
    
    # 2. Key Rotation (Allocated for Audio)
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="audio")
    
    if not available_keys:
        print("FAILED: No Gemini keys available for SSML. Returning original text.")
        return text
        
    last_error = None
    for i, key in enumerate(available_keys):
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for SSML...")
            from src.gemini_utils import get_gemini_model
            client, model_name = get_gemini_model(capability="text", api_key=key)
            from src.gemini_utils import gemini_generate_content_pacing
            response = await gemini_generate_content_pacing(
                client, 
                model_name, 
                contents=SSML_PROMPT.format(text=text),
                api_key=key
            )
            ssml_text = response.text
            
            # Basic cleanup to ensure it's just the SSML if the model adds markdown
            if "```xml" in ssml_text:
                ssml_text = ssml_text.split("```xml")[1].split("```")[0].strip()
            elif "```" in ssml_text:
                ssml_text = ssml_text.split("```")[1].split("```")[0].strip()
                
            if not ssml_text or "<speak>" not in ssml_text:
                print(f"WARNING: Key {i+1} returned invalid SSML. Trying next...")
                continue
            
            # 3. Save to Cache
            if chapter_id:
                try:
                    with Session(engine) as session:
                        ch = session.get(Chapter, chapter_id)
                        if ch:
                            ch.enhanced_script = ssml_text
                            session.add(ch)
                            session.commit()
                            print(f"CACHE SAVE: Stored SSML for chapter {chapter_id}")
                except: pass

            print(f"SUCCESS: SSML generated successfully using key {i+1}")
            return ssml_text
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                print(f"WARNING: Gemini Key {i+1} exhausted. Switching to next...")
                continue
            else:
                print(f"WARNING: Gemini Key {i+1} failed with error: {e}")
                if i < len(GEMINI_API_KEYS) - 1:
                    continue
                break
    
    print(f"ERROR: All Gemini keys failed for SSML. Falling back to plain text. Error: {last_error}")
    return text

def format_text_for_deepgram(text: str) -> str:
    """
    Format text according to Deepgram best practices for natural speech.
    Converts unsupported tags like [laughs] into compatible markers.
    Based on: https://developers.deepgram.com/docs/improving-aura-2-formatting
    """
    import re
    
    # 1. Convert emotional markers to Deepgram-compatible speech patterns
    text = text.replace("[laughs]", "um...")
    text = text.replace("[gasps]", "wow...")
    text = text.replace("[sighs]", ". . .")
    text = text.replace("[excitedly]", "")
    text = text.replace("[whispers]", "...")
    
    # Remove any remaining bracketed tags that aren't supported
    text = re.sub(r'\[\w+\]', '', text)
    
    # 2. Add comma before direct address names
    common_names = ['Jax', 'Emma', 'Maria', 'John', 'Sarah']
    for name in common_names:
        text = re.sub(rf'\b(Hello|Hey|Hi|Wait|Listen)\s+{name}\b', rf'\1, {name}', text, flags=re.IGNORECASE)
    
    # 3. Fix missing commas in common conversational patterns
    text = re.sub(r'\b(you know)\s+([A-Z])', r'\1, \2', text)
    text = re.sub(r'\b(I mean)\s+([A-Z])', r'\1, \2', text)
    text = re.sub(r'\b(honestly)\s+([A-Z])', r'\1, \2', text, flags=re.IGNORECASE)
    
    # 4. Ensure space before punctuation where needed
    # (Deepgram guide mentions spaces before ? and ! can improve emphasis)
    text = re.sub(r'(\w)(\?|!)', r'\1 \2', text)
    
    # 5. Clean up spaces
    text = re.sub(r'\s{2,}', ' ', text)
    
    return text.strip()

def get_deepgram_voice(voice_id: str) -> str:
    """
    Map ElevenLabs/generic voice IDs to Deepgram Aura-2 voices.
    Uses the most expressive, warm, and engaging voices for storytelling.
    
    Voice Selection (optimized for audiobooks):
    - Cordelia: Approachable, Warm, Polite - BEST for storytelling
    - Aries: Warm, Energetic, Caring - good for engaging narration
    - Helena: Caring, Natural, Positive, Friendly - audiobook friendly
    - Draco: British, Warm, Approachable, Trustworthy - professional narrator
    """
    voice_map = {
        # Default audiobook voice - Cordelia is specifically designed for storytelling
        "default": "aura-2-cordelia-en",
        
        # Map ElevenLabs IDs to expressive Deepgram voices
        "pNInz6obpgDQGcFmaJgB": "aura-2-draco-en",      # Adam -> Draco (British, Warm, Trustworthy narrator)
        "21m00Tcm4TlvDq8ikWAM": "aura-2-cordelia-en",   # Rachel -> Cordelia (Warm, Storytelling focus)
        
        # Additional voice options for variety
        "warm_female": "aura-2-cordelia-en",    # Approachable, Warm, Storytelling
        "warm_male": "aura-2-draco-en",         # British, Warm, Approachable
        "energetic_female": "aura-2-aries-en",  # Warm, Energetic, Caring
        "friendly_female": "aura-2-helena-en",  # Caring, Natural, Positive
        "expressive_female": "aura-2-aurora-en", # Cheerful, Expressive, Energetic
        "deep_male": "aura-2-neptune-en",       # Deep, Cinematic, Professional (Neptune)
        "assistant_female": "aura-2-asteria-en", # Friendly, Natural, Assistant (Asteria)
        # Podcast specific voices
        "aura-2-jax-en": "aura-2-orion-en",      # Jax -> Orion (Energetic, engaging)
        "aura-2-emma-en": "aura-2-athena-en",     # Emma -> Athena (Smart, witty, calm)
    }
    return voice_map.get(voice_id, "aura-2-neptune-en")

async def enhance_narrative_script(text: str, **kwargs) -> str:
    """
    Uses Gemini to rewrite the text with narrator-friendly punctuation 
    (ellipses for pauses, dashes for emphasis) to reduce robotic sound.
    Implements key rotation and database caching.
    """
    from src.database import Chapter, engine, Session
    from src.config import PODCAST_API_KEYS, GEMINI_API_KEYS
    
    # 1. Check Cache if chapter_id is provided
    chapter_id = kwargs.get('chapter_id')
    if chapter_id:
        with Session(engine) as session:
            ch = session.get(Chapter, chapter_id)
            if ch and ch.enhanced_script:
                print(f"CACHE HIT: Using existing enhanced script for chapter {chapter_id}")
                return ch.enhanced_script

    # 1. Key Rotation (Allocated for Audio)
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="audio")
    
    if not available_keys:
        return text
        
    prompt = f"""
    Act as a professional audiobook director. 
    Rewrite the following book text into a "Narrator's Script".
    
    GUIDELINES:
    1. Add ellipses (...) where a narrator should take a breath or pause for dramatic effect.
    2. Use dashes (—) to show a shift in thought or to emphasize a word.
    3. If a sentence is very long, break it into smaller, punchier phrases.
    4. Keep the story EXACTLY the same. Do not change words, only add punctuation for "pacing" and "prosody".
    5. Do not include any meta-commentary, just the rewritten script.
    
    TEXT TO REWRITE:
    {text[:4000]} 
    """
    
    last_error = None
    for i, key in enumerate(available_keys):
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Script Enhancement...")
            
            from src.gemini_utils import get_gemini_model
            client, model_name = get_gemini_model(capability="text", api_key=key)
            from src.gemini_utils import gemini_generate_content_pacing
            response = await gemini_generate_content_pacing(
                client, 
                model_name, 
                contents=prompt,
                api_key=key
            )
            enhanced_text = response.text.strip()
            
            # Clean up any markdown
            if "```" in enhanced_text:
                enhanced_text = enhanced_text.split("```")[1].split("```")[0].strip()
            
            # 3. Save to Cache if chapter_id provided
            if chapter_id:
                try:
                    with Session(engine) as session:
                        ch = session.get(Chapter, chapter_id)
                        if ch:
                            ch.enhanced_script = enhanced_text
                            session.add(ch)
                            session.commit()
                            print(f"CACHE SAVE: Stored enhanced script for chapter {chapter_id}")
                except Exception as cache_err:
                    print(f"WARNING: Failed to save to cache: {cache_err}")

            print(f"SUCCESS: Script enhanced for prosody using key {i+1} ({len(text)} -> {len(enhanced_text)} chars)")
            return enhanced_text
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                print(f"WARNING: Gemini Key {i+1} exhausted (Enhancement). Switching to next...")
                continue
            else:
                print(f"WARNING: Gemini Key {i+1} failed (Enhancement): {e}")
                continue
    
    print(f"ERROR: All Gemini keys failed for Script Enhancement. Using raw text. Error: {last_error}")
    return text

async def generate_audio_deepgram(text, output_path, voice_id="pNInz6obpgDQGcFmaJgB", title=None, author=None, chapter_id=None, is_podcast=False):
    """
    Generates audio using Deepgram Aura-2 TTS API.
    Automatically selects appropriate voice based on voice_id mapping.
    Applies enhanced text formatting for natural speech prosody.
    """
    if not DEEPGRAM_API_KEY:
        print("ERROR: DEEPGRAM_API_KEY is missing!")
        raise Exception("DEEPGRAM_API_KEY is missing!")
    
    # Get the appropriate Deepgram voice
    deepgram_voice = get_deepgram_voice(voice_id)
    assistant_voice = "aura-2-asteria-en"
    narrator_voice = "aura-2-neptune-en" # Default to Neptune as requested
    
    print(f"--- Generating Premium Audiobook with Deepgram ---")
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }

    async def get_audio_bytes(t, v):
        u = f"https://api.deepgram.com/v1/speak?model={v}"
        p = {"text": t}
        r = requests.post(u, headers=headers, json=p)
        if r.status_code == 200:
            return r.content
        raise Exception(f"Deepgram Error: {r.status_code} - {r.text}")

    # === STEP 1: GENERATE ASSISTANT INTRO (Voice A) ===
    # Skip intro for podcasts to keep them snappy
    intro_bytes = b""
    if not is_podcast and title and author and len(text) > 500:
        intro_text = f"Hi! I'm your Book two Vision assistant. I've prepared a special, deep-sound narration of {title} by {author} for you. Sit back, relax, and enjoy the story."
        print(f"INFO: Generating Assistant Intro (Asteria)...")
        try:
            intro_bytes = await asyncio.to_thread(lambda: requests.post(
                f"https://api.deepgram.com/v1/speak?model={assistant_voice}", 
                headers=headers, 
                json={"text": intro_text}
            ).content)
        except:
            print("WARNING: Intro generation failed, skipping.")

    # === STEP 2: ENHANCE STORY SCRIPT (Gemini Prosody) ===
    enhanced_text = text
    if not is_podcast:
        print(f"INFO: Enhancing story script with Gemini for natural pacing...")
        enhanced_text = await enhance_narrative_script(text, chapter_id=chapter_id)
    else:
        print(f"INFO: Skipping script enhancement for podcast segment.")
    
    # === STEP 3: GENERATE STORY (Use requested voice) ===
    # For podcasts, we MUST use the deepgram_voice determined from voice_id
    current_voice = deepgram_voice if is_podcast else narrator_voice
    print(f"INFO: Generating Audio with Deepgram ({current_voice})...")
    
    formatted_text = format_text_for_deepgram(enhanced_text)
    
    print(f"INFO: Text formatted for natural TTS ({len(text)} -> {len(formatted_text)} chars)")
    
    # Deepgram has a 2000 character limit per request. We must chunk.
    def chunk_text_by_sentence(text, max_length=1900):
        # Rough split by common sentence enders
        sentences = text.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks

    try:
        def process_chunks():
            chunks = chunk_text_by_sentence(formatted_text)
            if len(chunks) > 1:
                print(f"INFO: Text too long for single request. Split into {len(chunks)} chunks.")
            
            all_audio = intro_bytes # Start with assistant intro (empty if podcast)
            for i, chunk in enumerate(chunks):
                if not chunk.strip(): continue
                payload = {"text": chunk}
                print(f"  -> Sending chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                # Use current_voice (either requested voice_id or narrator default)
                u = f"https://api.deepgram.com/v1/speak?model={current_voice}"
                response = requests.post(u, headers=headers, json=payload)
                if response.status_code == 200:
                    all_audio += response.content
                else:
                    error_msg = f"Deepgram API Error on chunk {i+1}: {response.status_code} - {response.text}"
                    print(error_msg)
                    raise Exception(error_msg)
            
            with open(output_path, "wb") as f:
                f.write(all_audio)
            return output_path
            
        result = await asyncio.to_thread(process_chunks)
        print(f"SUCCESS: Deepgram audio saved: {result}")
        return result
    except Exception as e:
        print(f"❌ Deepgram failed: {e}")
        raise e

async def generate_audio(text, output_path="audiobook.mp3", voice_id="pNInz6obpgDQGcFmaJgB", stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True, provider="elevenlabs", speaking_rate=1.0, title=None, author=None, chapter_id=None, is_podcast=False):
    """
    Generates audio using the specified provider with automatic fallback.
    Priority: Deepgram -> Edge TTS (inbuilt)
    """
    print(f"--- Generating audio with provider: {provider} (Rate: {speaking_rate})")
    
    # --- Step 0: Natural Narration SSML ---
    processed_text = text
    if not is_podcast and provider in ["deepgram", "elevenlabs"]:
        processed_text = await generate_ssml(text, chapter_id=chapter_id)
    elif is_podcast:
        print("INFO: Skipping SSML generation for podcast segment.")
    
    # Deepgram with automatic fallback to edge-tts
    if provider == "deepgram":
        if not DEEPGRAM_API_KEY:
            print("WARNING: Deepgram key missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        
        try:
            return await generate_audio_deepgram(processed_text, output_path, voice_id, title=title, author=author, chapter_id=chapter_id, is_podcast=is_podcast)
        except Exception as e:
            print(f"WARNING: Deepgram failed: {e}. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
    
    # Edge TTS (inbuilt)
    elif provider == "inbuilt":
        return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        
    # Voice Clone (Colab XTTS v2)
    elif provider == "voice_clone":
        from src.state import state
        if not state.voice_sample_path or not state.colab_url:
            print("WARNING: Voice sample or Colab URL missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        return await generate_audio_voice_clone(text, output_path, state.voice_sample_path, state.colab_url)
    
    
    # ElevenLabs with fallback
    elif provider == "elevenlabs":
        if not ELEVENLABS_API_KEY:
            print("WARNING: ElevenLabs key missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        return await generate_audio_elevenlabs(processed_text, output_path, voice_id, stability, similarity_boost, style, use_speaker_boost)
    
    # Default fallback
    else:
        print(f"WARNING: Unknown provider '{provider}'. Using Edge TTS.")
        return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)

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

async def generate_audio_voice_clone(text, output_path, voice_sample_path, colab_url):
    """
    Generates audio using a custom XTTS v2 model hosted on Google Colab via ngrok.
    """
    import base64
    import json
    
    print(f"Generating cloned audio for {len(text)} characters using Colab API...")
    
    # Read the voice sample as base64
    try:
        with open(voice_sample_path, "rb") as audio_file:
            speaker_wav_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading voice sample: {e}")
        raise Exception("Failed to read voice sample.")

    url = f"{colab_url.rstrip('/')}/clone"
    
    payload = {
        "text": text,
        "speaker_wav_base64": speaker_wav_base64,
        "language": "en"
    }
    
    try:
        def make_request():
            return requests.post(url, json=payload, timeout=120)  # 2 minute timeout since generation is slow
            
        response = await asyncio.to_thread(make_request)
        
        if response.status_code == 200:
            def write_file():
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
                
            result = await asyncio.to_thread(write_file)
            print(f"✅ Cloned audio saved to {result}")
            return result
        else:
            error_msg = f"Colab Voice Clone Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Exception in Voice Clone TTS: {e}")
        print("Falling back to Edge TTS...")
        return await generate_audio_edge(text, output_path)

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






# ----------------------------------------------------------------------------
# ENHANCED TTS FORMATTING FOR DEEPGRAM AURA-2
# Based on: https://developers.deepgram.com/docs/improving-aura-2-formatting
# ----------------------------------------------------------------------------

def enhance_text_for_natural_tts(text: str) -> str:
    """
    Comprehensive text enhancement for natural Deepgram Aura-2 speech.
    Applies punctuation-based prosody control since Aura-2 doesn't support SSML.
    """
    import re
    
    # Skip if text is too short
    if len(text) < 50:
        return text
    
    result = text
    
    # === 1. EXPAND ABBREVIATIONS ===
    abbreviations = {
        r'\bDr\.': 'Doctor',
        r'\bMr\.': 'Mister',
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Miss',
        r'\bProf\.': 'Professor',
        r'\bSt\.': 'Street',
        r'\bAve\.': 'Avenue',
        r'\bBlvd\.': 'Boulevard',
        r'\bCo\.': 'Company',
        r'\betc\.': 'et cetera',
        r'\bi\.e\.': 'that is',
        r'\be\.g\.': 'for example',
        r'\bvs\.': 'versus',
        r'\bft\.': 'feet',
        r'\bin\.': 'inches',
        r'\blbs?\.': 'pounds',
        r'\bkg\.': 'kilograms',
        r'\bkm\.': 'kilometers',
    }
    for abbr, expansion in abbreviations.items():
        result = re.sub(abbr, expansion, result, flags=re.IGNORECASE)
    
    # === 2. NUMBER FORMATTING ===
    def number_to_words(match):
        num = int(match.group(0))
        if num > 9999:
            return match.group(0)  # Keep large numbers as-is
        
        ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                'seventeen', 'eighteen', 'nineteen']
        tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else '-' + ones[num % 10])
        elif num < 1000:
            return ones[num // 100] + ' hundred' + ('' if num % 100 == 0 else ' and ' + number_to_words(type('obj', (object,), {'group': lambda s, x: str(num % 100)})()))
        else:
            thousands = num // 1000
            remainder = num % 1000
            result = (ones[thousands] if thousands < 20 else tens[thousands // 10] + '-' + ones[thousands % 10]) + ' thousand'
            if remainder > 0:
                result += ' ' + number_to_words(type('obj', (object,), {'group': lambda s, x: str(remainder)})())
            return result
    
    # Convert standalone numbers (1-99) to words, but not years or large numbers
    result = re.sub(r'\b([1-9]|[1-4][0-9]|50)\b(?![0-9])', 
                    lambda m: number_to_words(m) if int(m.group(0)) <= 50 else m.group(0), 
                    result)
    
    # === 3. ADD NATURAL PAUSES ===
    
    # Add comma before direct address names
    common_names = ['Adam', 'Alex', 'Anna', 'Ben', 'Charlie', 'David', 'Elena', 'Emma', 
                   'Jake', 'James', 'Jane', 'John', 'Kate', 'Lisa', 'Maria', 'Michael',
                   'Sarah', 'Tom', 'Jax', 'Max', 'Sam', 'Lucy', 'Mark']
    for name in common_names:
        result = re.sub(rf'\b(Hello|Hey|Hi|Oh|Wait|Listen|Look|Well|Okay|Thanks|Sorry)\s+({name})\b', 
                       rf'\1, \2', result, flags=re.IGNORECASE)
    
    # Add pauses after introductory phrases
    intro_phrases = [
        (r'^(However)\s', r'\1,... '),
        (r'^(Therefore)\s', r'\1,... '),
        (r'^(Moreover)\s', r'\1,... '),
        (r'^(Furthermore)\s', r'\1,... '),
        (r'^(In fact)\s', r'\1,... '),
        (r'^(Actually)\s', r'\1,... '),
        (r'^(Meanwhile)\s', r'\1,... '),
        (r'^(Suddenly)\s', r'\1,... '),
    ]
    for pattern, replacement in intro_phrases:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Add ellipsis before dramatic moments
    dramatic_words = ['suddenly', 'unexpectedly', 'shockingly', 'terrifyingly', 'amazingly']
    for word in dramatic_words:
        result = re.sub(rf'\. ({word})', rf'. ...\1', result, flags=re.IGNORECASE)
    
    # === 4. BREAK LONG SENTENCES ===
    def break_long_sentence(sentence):
        words = sentence.split()
        if len(words) <= 20:
            return sentence
        
        # Find natural break points
        break_words = [' and ', ' but ', ' so ', ' because ', ' although ', ' however ', ' therefore ', ' which ', ' where ', ' when ']
        
        for bw in break_words:
            if bw in sentence.lower():
                # Split at the break word, keep it with the second part
                parts = re.split(rf'({bw})', sentence, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) >= 3 and len(parts[0].split()) >= 5:
                    return parts[0].rstrip() + ',' + parts[1] + parts[2]
        
        return sentence
    
    # Apply to each sentence
    sentences = re.split(r'(?<=[.!?])\s+', result)
    result = ' '.join(break_long_sentence(s) for s in sentences)
    
    # === 5. CLEAN UP ===
    
    # Remove multiple spaces
    result = re.sub(r'\s{2,}', ' ', result)
    
    # Ensure space after punctuation
    result = re.sub(r'([.!?,])([A-Za-z])', r'\1 \2', result)
    
    # Don't stack multiple ellipses
    result = re.sub(r'\.{4,}', '...', result)
    
    # Remove ellipsis at start if it's the only thing
    result = result.lstrip('.')
    
    return result.strip()


async def prepare_text_for_tts_with_llm(text: str, max_chars: int = 8000) -> str:
    """
    Use Gemini to reformat text for optimal TTS naturalness.
    Falls back to rule-based enhancement if LLM fails.
    """
    from src.config import GEMINI_API_KEY
    
    # Truncate if too long for LLM processing
    if len(text) > max_chars:
        text = text[:max_chars]
    
    try:
        from google import genai
        from src.prompts import TTS_PREPROCESSING_PROMPT
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=TTS_PREPROCESSING_PROMPT.format(text=text)
        )
        
        processed_text = response.text.strip()
        
        # Basic validation - should be similar length and have content
        if len(processed_text) < len(text) * 0.5 or len(processed_text) < 100:
            print("⚠️ LLM preprocessing returned suspicious output, using rule-based fallback")
            return enhance_text_for_natural_tts(text)
        
        print(f"✅ LLM preprocessing complete ({len(text)} -> {len(processed_text)} chars)")
        return processed_text
        
    except Exception as e:
        print(f"⚠️ LLM preprocessing failed: {e}, using rule-based fallback")
        return enhance_text_for_natural_tts(text)


def chunk_text_for_tts(text: str, max_chunk_size: int = 3000) -> list:
    """
    Split text into natural chunks for TTS processing.
    Breaks at paragraph, sentence, or phrase boundaries.
    """
    import re
    
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first
    paragraphs = re.split(r'\n\n+', text)
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            # Paragraph is too big to add, need to split it
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            if len(para) <= max_chunk_size:
                current_chunk = para + "\n\n"
            else:
                # Split large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Add ellipsis at the end of chunks (except last) for natural continuation pause
    for i in range(len(chunks) - 1):
        if not chunks[i].endswith('...'):
            chunks[i] = chunks[i].rstrip('.') + '...'
    
    return chunks



def slow_down_for_audiobook(text: str) -> str:
    """
    Add extra pauses to slow down Deepgram Aura-2 speech for audiobook narration.
    Since Aura-2 doesn't have a speed parameter, we use punctuation to control pace.
    """
    import re
    
    result = text
    
    # === ADD PAUSES BETWEEN SENTENCES ===
    # Replace single period with period + ellipsis for longer pause
    result = re.sub(r'\.\s+', '. ... ', result)
    
    # === ADD PAUSES AT PARAGRAPH BREAKS ===
    result = re.sub(r'\n\n', '\n\n... ', result)
    
    # === ADD PAUSES AFTER DIALOGUE ===
    # After closing quotes, add a pause
    result = re.sub(r'([.!?])"\s+', r'\1" ... ', result)
    result = re.sub(r"([.!?])'\s+", r"\1' ... ", result)
    
    # === ADD PAUSES FOR DRAMATIC EFFECT ===
    # Before important transition words
    transition_words = ['However', 'But', 'Then', 'Suddenly', 'Finally', 'Meanwhile', 
                       'Later', 'Eventually', 'Afterward', 'Soon', 'Next']
    for word in transition_words:
        result = re.sub(rf'\. ({word})', rf'. ... \1', result, flags=re.IGNORECASE)
    
    # === ADD COMMA PAUSES ===
    # Add slight pauses after long clauses (more than 8 words before comma)
    # This is approximated by adding ellipsis after commas following long stretches
    result = re.sub(r',\s+', ', ', result)  # Normalize comma spacing
    
    # === ADD PAUSES BEFORE IMPORTANT WORDS ===
    dramatic_starters = ['He', 'She', 'They', 'It', 'The', 'A', 'An']
    for word in dramatic_starters:
        # Only after periods, not in the middle of sentences
        result = re.sub(rf'\. \.\.\.  ({word})\s', rf'. ... {word} ', result)
    
    # === CLEAN UP ===
    # Remove excessive ellipses (more than one set)
    result = re.sub(r'(\.\s*){4,}', '... ', result)
    result = re.sub(r'\s{2,}', ' ', result)
    
    return result.strip()





async def prepare_audiobook_text(text: str, book_title: str = "this audiobook", author: str = "the author") -> str:
    """
    Prepare text for professional audiobook narration using Gemini.
    Applies all the formatting rules for natural, engaging TTS output.
    
    Args:
        text: The raw book text
        book_title: Title of the book
        author: Author name
    
    Returns:
        Formatted text optimized for TTS narration
    """
    from src.config import GEMINI_API_KEY
    
    try:
        from google import genai
        from src.prompts import AUDIOBOOK_NARRATOR_PROMPT
        
        print(f"INFO: Preparing audiobook narration for: {book_title}")
        
        # For very long texts, process in chunks
        max_chunk = 8000
        if len(text) > max_chunk:
            # Process intro
            intro_text = text[:max_chunk]
            processed_intro = await _process_audiobook_chunk(intro_text, book_title, author, is_intro=True)
            
            # For now, just add pauses to the rest using rule-based approach
            rest_text = text[max_chunk:]
            processed_rest = slow_down_for_audiobook(enhance_text_for_natural_tts(rest_text))
            
            full_text = processed_intro + "\n\n... " + processed_rest
            
            # Add outro
            full_text += "\n\n... Thank you for listening."
            
            return full_text
        else:
            return await _process_audiobook_chunk(text, book_title, author, is_intro=True, is_outro=True)
            
    except Exception as e:
        print(f"⚠️ Audiobook preparation failed: {e}, using rule-based fallback")
        # Fallback to rule-based processing
        result = f"You are listening to the audiobook of {book_title}. "
        if author:
            result += f"Written by {author}. "
        result += "... "
        result += slow_down_for_audiobook(enhance_text_for_natural_tts(text))
        result += " ... Thank you for listening."
        return result


async def _process_audiobook_chunk(text: str, book_title: str, author: str, 
                                   is_intro: bool = False, is_outro: bool = False) -> str:
    """Process a chunk of text through LLM for audiobook formatting."""
    from src.config import GEMINI_API_KEY
    from google import genai
    from src.prompts import AUDIOBOOK_NARRATOR_PROMPT
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = AUDIOBOOK_NARRATOR_PROMPT.format(
        text=text,
        book_title=book_title,
        author=author
    )
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    
    processed = response.text.strip()
    
    # Validate output
    if len(processed) < len(text) * 0.3:
        print("⚠️ LLM output too short, using rule-based fallback")
        result = ""
        result = ""
        if is_intro:
            result = f"You are listening to the audiobook of {book_title}. "
            if author:
                result += f"Written by {author}. "
            result += "... "
        result += slow_down_for_audiobook(enhance_text_for_natural_tts(text))
        if is_outro:
            result += " ... Thank you for listening."
        return result
    
    print(f"✅ Audiobook text prepared ({len(text)} -> {len(processed)} chars)")
    return processed


def format_for_professional_narration(text: str, book_title: str = "", author: str = "") -> str:
    """
    Rule-based professional narration formatting (sync version).
    Adds proper pauses and formatting for audiobook quality.
    """
    import re
    
    result = text
    
    # === ADD INTRO ===
    if book_title:
        intro = f"You are listening to the audiobook of {book_title}. "
        if author:
            intro += f"Written by {author}. "
        intro += "... "
        result = intro + result
    
    # === FORMAT CHAPTER HEADINGS ===
    # Add long pauses around chapter titles
    result = re.sub(r'(Chapter\s+\d+[:\.]?\s*[^\n]*)', r'... \1 ...', result, flags=re.IGNORECASE)
    result = re.sub(r'(CHAPTER\s+\d+[:\.]?\s*[^\n]*)', r'... \1 ...', result)
    
    # === ADD SENTENCE PAUSES ===
    # Every period gets an ellipsis for natural pause
    result = re.sub(r'\.\s+(?=[A-Z])', '. ... ', result)
    
    # === ADD PARAGRAPH PAUSES ===
    result = re.sub(r'\n\n+', '\n\n... ', result)
    
    # === ADD DIALOGUE PAUSES ===
    result = re.sub(r'([.!?])"\s+', r'\1" ... ', result)
    
    # === ADD DRAMATIC PAUSES ===
    dramatic_words = ['Suddenly', 'However', 'But', 'Then', 'Meanwhile', 'Finally',
                     'Unfortunately', 'Fortunately', 'Surprisingly', 'Amazingly']
    for word in dramatic_words:
        result = re.sub(rf'\. ({word})', rf'. ... \1', result, flags=re.IGNORECASE)
    
    # === EXPAND COMMON ABBREVIATIONS ===
    abbrevs = {
        r'\bDr\.': 'Doctor',
        r'\bMr\.': 'Mister', 
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Miss',
        r'\bProf\.': 'Professor',
    }
    for abbr, expanded in abbrevs.items():
        result = re.sub(abbr, expanded, result)
    
    # === ADD OUTRO ===
    result = result.rstrip() + " ... Thank you for listening."
    
    # === CLEAN UP ===
    result = re.sub(r'(\.\s*){4,}', '... ', result)
    result = re.sub(r'\s{3,}', ' ', result)
    
    return result

