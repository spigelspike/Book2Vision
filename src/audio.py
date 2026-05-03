import asyncio
import requests

from google import genai
from src.config import ELEVENLABS_API_KEY, GEMINI_API_KEY, DEEPGRAM_API_KEY, POLLINATIONS_API_KEY
from src.prompts import SSML_PROMPT

# Configure Gemini
# genai.configure(api_key=GEMINI_API_KEY) # Not needed with new SDK client

async def generate_ssml(text):
    """
    Rewrites text into SSML using Gemini for natural narration.
    """
    print("Generating SSML with Gemini...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model='gemini-2.0-flash', contents=SSML_PROMPT.format(text=text))
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

def format_text_for_deepgram(text: str) -> str:
    """
    Format text according to Deepgram best practices for natural speech.
    Based on: https://developers.deepgram.com/docs/improving-aura-2-formatting
    """
    import re
    
    # Preserve emotional markers like [laughs], [gasps], [sighs]
    # We'll temporarily replace them to avoid punctuation changes
    markers = re.findall(r'\[\w+\]', text)
    for i, marker in enumerate(markers):
        text = text.replace(marker, f"__MARKER_{i}__", 1)
    
    # Add comma before direct address names (e.g., "Hello Maria" -> "Hello, Maria")
    # Common names in podcast context
    common_names = ['Jax', 'Emma', 'Maria', 'John', 'Sarah']
    for name in common_names:
        text = re.sub(rf'\b(Hello|Hey|Hi|Wait|Listen)\s+{name}\b', rf'\1, {name}', text, flags=re.IGNORECASE)
    
    # Fix missing commas in common conversational patterns
    text = re.sub(r'\b(you know)\s+([A-Z])', r'\1, \2', text)  # "you know I" -> "you know, I"
    text = re.sub(r'\b(I mean)\s+([A-Z])', r'\1, \2', text)  # "I mean it" -> "I mean, it"
    text = re.sub(r'\b(honestly)\s+([A-Z])', r'\1, \2', text, flags=re.IGNORECASE)  # "honestly I" -> "honestly, I"
    text = re.sub(r'\b(like)\s+([A-Z])', r'\1, \2', text)  # "like I" -> "like, I" (only if followed by capital)
    
    # Ensure space before punctuation where needed
    text = re.sub(r'(\w)(\?|!)', r'\1 \2', text)  # Add space before ? and ! if missing
    text = re.sub(r'\s{2,}', ' ', text)  # Remove double spaces
    
    # Restore emotional markers
    for i, marker in enumerate(markers):
        text = text.replace(f"__MARKER_{i}__", marker)
    
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
    }
    return voice_map.get(voice_id, "aura-2-cordelia-en")

async def generate_audio_deepgram(text, output_path, voice_id="pNInz6obpgDQGcFmaJgB", title=None, author=None):
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
    print(f"🎧 Generating audio using Deepgram Aura-2 ({deepgram_voice})...")
    
    url = f"https://api.deepgram.com/v1/speak?model={deepgram_voice}"
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # === SMART FORMATTING BASED ON TEXT LENGTH ===
    # Short texts (like podcast segments) - just use basic formatting
    # Long texts (audiobooks) - use professional narration with intro/outro
    if len(text) < 500:
        # Short text - skip professional narration (no intro/outro)
        formatted_text = format_text_for_deepgram(text)
    else:
        # Long text - apply full professional narration
        # Only pass title/author if provided (implies audiobook mode)
        professional_text = format_for_professional_narration(text, book_title=title, author=author)
        formatted_text = format_text_for_deepgram(professional_text)
    
    print(f"📝 Text formatted for natural TTS ({len(text)} -> {len(formatted_text)} chars)")
    
    payload = {
        "text": formatted_text
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
            print(f"✅ Deepgram audio saved: {result}")
            return result
        else:
            error_msg = f"Deepgram API Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        print(f"❌ Deepgram failed: {e}")
        raise e

async def generate_audio(text, output_path="audiobook.mp3", voice_id="pNInz6obpgDQGcFmaJgB", stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True, provider="elevenlabs", speaking_rate=1.0, title=None, author=None):
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
            return await generate_audio_deepgram(text, output_path, voice_id, title=title, author=author)
        except Exception as e:
            print(f"⚠️  Deepgram failed: {e}. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
    
    # Edge TTS (inbuilt)
    elif provider == "inbuilt":
        return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        
    # Voice Clone (Colab XTTS v2)
    elif provider == "voice_clone":
        from src.state import state
        if not state.voice_sample_path or not state.colab_url:
            print("⚠️ Voice sample or Colab URL missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        return await generate_audio_voice_clone(text, output_path, state.voice_sample_path, state.colab_url)
    
    
    # Pollinations
    elif provider == "pollinations":
        if not POLLINATIONS_API_KEY:
            print("⚠️  Pollinations API key missing. Falling back to Inbuilt (Edge TTS).")
            return await generate_audio_edge(text, output_path, voice_id, rate=speaking_rate)
        return await generate_audio_pollinations(text, output_path, voice_id)

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

async def generate_audio_pollinations(text, output_path, voice_id="nova", model="elevenlabs"):
    """
    Generates audio using Pollinations AI TTS API.
    """
    print(f"Generating audio for {len(text)} characters using Pollinations AI ({voice_id})...")
    if not POLLINATIONS_API_KEY:
        raise Exception("POLLINATIONS_API_KEY is missing!")
    
    url = "https://gen.pollinations.ai/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use ElevenLabs mapped voice if requested
    mapped_voice = voice_id
    if voice_id == "pNInz6obpgDQGcFmaJgB":
        mapped_voice = "onyx"
    elif voice_id == "21m00Tcm4TlvDq8ikWAM":
        mapped_voice = "nova"
    
    payload = {
        "model": model,
        "input": text,
        "voice": mapped_voice
    }
    
    try:
        def make_request():
            return requests.post(url, headers=headers, json=payload, timeout=60)
            
        response = await asyncio.to_thread(make_request)
        
        if response.status_code == 200:
            def write_file():
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
                
            result = await asyncio.to_thread(write_file)
            print(f"✅ Pollinations audio saved to {result}")
            return result
        else:
            error_msg = f"Pollinations API Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Exception in Pollinations TTS: {e}")
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
        
        print(f"📖 Preparing audiobook narration for: {book_title}")
        
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

