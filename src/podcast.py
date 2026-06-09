import os
import json
import asyncio
import time
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from google import genai
from openai import AsyncOpenAI
from src.config import OPENROUTER_API_KEY, GEMINI_API_KEYS, PODCAST_API_KEYS
from src.audio import generate_audio
from src.prompts import PODCAST_PROMPT

@dataclass
class VoiceConfig:
    """Configuration for a podcast host's voice."""
    elevenlabs_id: str
    edge_voice: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    speaking_rate: float = 1.0

@dataclass
class HostProfile:
    """Profile for a podcast host."""
    name: str
    gender: str
    personality: str
    voice: VoiceConfig

# Enhanced host configurations
HOSTS = {
    "Jax": HostProfile(
        name="Jax",
        gender="Male",
        personality="High energy, hype man, uses modern slang (but not cringe), treats plot twists like breaking celebrity gossip. Gets VERY excited about action or drama.",
        voice=VoiceConfig(
            elevenlabs_id="pNInz6obpgDQGcFmaJgB",  # Adam
            edge_voice="en-US-GuyNeural",
            stability=0.4,  # More variable for excitement
            similarity_boost=0.8,
            style=0.6,  # Higher style for personality
            speaking_rate=1.0  # Slowed down from 1.1
        )
    ),
    "Emma": HostProfile(
        name="Emma",
        gender="Female",
        personality="Witty, sharp, slightly sarcastic but loves a good story. Keeps Jax grounded, adds intellectual context but keeps it fun/accessible. Loves analyzing character motives.",
        voice=VoiceConfig(
            elevenlabs_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
            edge_voice="en-US-AriaNeural",
            stability=0.6,  # More controlled
            similarity_boost=0.75,
            style=0.2,  # Subtle style
            speaking_rate=0.9  # Slowed down from 1.0
        )
    )
}

FALLBACK_SCRIPT = [
    {"speaker": "Jax", "text": "Yo yo yo! Welcome back to Booked and Busy!"},
    {"speaker": "Emma", "text": "Hey everyone! We've got a technical hiccup on our end."},
    {"speaker": "Jax", "text": "Yeah, the AI gremlins are acting up. But we'll be back with your book review real soon!"},
    {"speaker": "Emma", "text": "In the meantime, why don't you drop a comment about what you're reading? We'd love to hear from you!"},
    {"speaker": "Jax", "text": "Stay booked and stay busy, fam! Catch you next time!"}
]

def _create_error_fallback(error_type: str, error_detail: str) -> List[Dict]:
    """
    Create a more informative fallback script based on the error.
    
    Args:
        error_type: Short error category (e.g., "API Error", "Invalid Key")
        error_detail: More detailed explanation
        
    Returns:
        Fallback script with error information
    """
    return [
        {"speaker": "Jax", "text": "Yo yo yo! Welcome back to Booked and Busy!"},
        {"speaker": "Emma", "text": f"We're having some trouble on our end. Error: {error_type}."},
        {"speaker": "Jax", "text": f"{error_detail}"},
        {"speaker": "Emma", "text": "Check the server logs for more details, or verify your API configuration."},
        {"speaker": "Jax", "text": "We'll be back soon! Stay booked and stay busy, fam!"}
    ]

class PodcastGenerator:
    """Handles podcast script and audio generation."""
    
    def __init__(self, api_key: str, hosts: Dict[str, HostProfile] = HOSTS):
        """
        Initialize the podcast generator.
        
        Args:
            api_key: OpenRouter API key
            hosts: Dictionary of host profiles
        """
        if not api_key:
            print("WARNING: OPENROUTER_API_KEY is not set")
            print("INFO: Podcast generation will use fallback scripts only")
        
        self.api_key = api_key
        self.hosts = hosts
        
        # Configure OpenAI client for OpenRouter API only if key exists
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=30.0,
                max_retries=0,  # We handle retries manually
                default_headers={
                    "HTTP-Referer": "https://book2vision.app",
                    "X-Title": "Book2Vision Podcast Generator"
                }
            )
        else:
            self.client = None
    
    def _create_error_fallback(self, error_type: str, error_detail: str) -> List[Dict]:
        """
        Create a more informative fallback script based on the error.
        
        Args:
            error_type: Short error category (e.g., "API Error", "Invalid Key")
            error_detail: More detailed explanation
            
        Returns:
            Fallback script with error information
        """
        return [
            {"speaker": "Jax", "text": "Yo yo yo! Welcome back to Booked and Busy!"},
            {"speaker": "Emma", "text": f"We're having some trouble on our end. Error: {error_type}."},
            {"speaker": "Jax", "text": f"{error_detail}"},
            {"speaker": "Emma", "text": "Check the server logs for more details, or verify your API configuration."},
            {"speaker": "Jax", "text": "We'll be back soon! Stay booked and stay busy, fam!"}
        ]
        
    def _format_prompt(self, text: str, host1: str = "Jax", host2: str = "Emma") -> str:
        """Format the podcast prompt with host information."""
        h1 = self.hosts[host1]
        h2 = self.hosts[host2]
        
        return PODCAST_PROMPT.format(
            host1_name=h1.name,
            host1_gender=h1.gender,
            host1_personality=h1.personality,
            host2_name=h2.name,
            host2_gender=h2.gender,
            host2_personality=h2.personality,
            text=text
        )
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean up JSON response from various markdown formats."""
        response_text = response_text.strip()
        
        # 1. Remove markdown code blocks if they exist
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        # 2. Find the actual JSON boundaries (first [ or { and last ] or })
        # This handles cases where the AI adds "Here is the JSON:" text
        start_idx = response_text.find("[")
        if start_idx == -1:
            start_idx = response_text.find("{")
            
        end_idx = response_text.rfind("]")
        if end_idx == -1:
            end_idx = response_text.rfind("}")
            
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            response_text = response_text[start_idx:end_idx+1]
            
        return response_text.strip()
    
    def _validate_script(self, script: List[Dict]) -> Tuple[bool, str]:
        """
        Validate the generated script format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(script, list):
            return False, "Script must be a list"
        
        if len(script) == 0:
            return False, "Script is empty"
        
        valid_speakers = set(self.hosts.keys())
        
        for i, segment in enumerate(script):
            if not isinstance(segment, dict):
                return False, f"Segment {i} is not a dictionary"
            
            if "speaker" not in segment or "text" not in segment:
                return False, f"Segment {i} missing 'speaker' or 'text' field"
            
            if segment["speaker"] not in valid_speakers:
                return False, f"Invalid speaker '{segment['speaker']}' in segment {i}"
            
            if not segment["text"] or not isinstance(segment["text"], str):
                return False, f"Invalid or empty text in segment {i}"
        
        return True, ""
    
    async def generate_script_gemini(self, text: str, max_length: int = 15000) -> List[Dict]:
        """Generate a podcast script using Gemini 2.0 Flash with key rotation."""
        print("--- Generating podcast script with Gemini AI...")
        
        # Using allocated keys (Podcast Key first)
        from src.config import get_allocated_keys
        available_keys = get_allocated_keys(purpose="podcast")
        if not available_keys:
             raise ValueError("No Gemini API keys found")
        
        last_error = None
        for i, key in enumerate(available_keys):
            try:
                print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Scripting...")
                from src.gemini_utils import get_gemini_model
                client, model_name = get_gemini_model(capability="text", api_key=key)
                input_text = text[:max_length]
                prompt = self._format_prompt(input_text)
                
                from src.gemini_utils import gemini_generate_content_pacing
                response = await gemini_generate_content_pacing(
                    client, 
                    model_name, 
                    contents=[
                        "You are an expert podcast script writer. Create an engaging, conversational script in valid JSON format. Return ONLY the JSON.",
                        prompt
                    ],
                    api_key=key
                )
                
                response_text = response.text
                cleaned_text = self._clean_json_response(response_text)
                script = json.loads(cleaned_text)
                
                is_valid, error_msg = self._validate_script(script)
                if not is_valid:
                    raise ValueError(f"Script validation failed: {error_msg}")
                    
                print(f"Gemini successfully generated {len(script)} segments using key {i+1}")
                return script
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    print(f"WARNING: Gemini Key {i+1} exhausted. Switching to next...")
                    continue
                else:
                    print(f"Gemini Key {i+1} failed with error: {e}")
                    # If it's not a quota error, we might still want to try the next key if it's a generic failure
                    if i < len(available_keys) - 1:
                        print("  -> Attempting with next key anyway...")
                        continue
                    break
        
        print(f"All Gemini keys failed. Last error: {last_error}")
        raise last_error

    async def generate_script_pollinations(self, text: str) -> List[Dict]:
        """Ultimate fallback: Use Pollinations with DeepSeek."""
        print("--- Using Pollinations/DeepSeek as Ultimate Fallback...")
        print("WARNING: OpenRouter failed. Falling back to Pollinations...")
        try:
            prompt = self._format_prompt(text[:5000])
            # Use GET for more reliable free-tier response
            import urllib.parse
            # Force JSON format and concise response
            encoded_prompt = urllib.parse.quote(f"Create a podcast script in valid JSON format: [{{'speaker': 'Jax', 'text': '...'}}, ...]. Return ONLY the JSON array. Content: {prompt}")
            url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&json=true"
            
            def make_request():
                return requests.get(url, timeout=60)
            
            response = await asyncio.to_thread(make_request)
            response_text = response.text.strip()
            
            # Clean up potential markdown or garbage
            cleaned_text = self._clean_json_response(response_text)
            
            # If still starts with something else, try to find the first [
            if not (cleaned_text.startswith('[') or cleaned_text.startswith('{')):
                start_idx = cleaned_text.find('[')
                if start_idx != -1:
                    end_idx = cleaned_text.rfind(']')
                    if end_idx != -1:
                        cleaned_text = cleaned_text[start_idx:end_idx+1]
            
            script = json.loads(cleaned_text)
            
            # If it's a dict, try to find the list inside or wrap it
            if isinstance(script, dict):
                # Common wrappers
                for key in ['segments', 'script', 'episodes', 'content']:
                    if key in script and isinstance(script[key], list):
                        script = script[key]
                        break
                
                # Check again if it's still a dict
                if isinstance(script, dict):
                    if 'speaker' in script and 'text' in script:
                        script = [script]
                    else:
                        # Try to find any list in the dict
                        found_list = False
                        for val in script.values():
                            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and ('speaker' in val[0] or 'text' in val[0]):
                                script = val
                                found_list = True
                                break
                        if not found_list:
                             # Just wrap whatever we have if it looks remotely like a segment
                             if any(k in script for k in ['speaker', 'text', 'role', 'content']):
                                 script = [script]
            
            # If still not a list, raise error
            if not isinstance(script, list):
                 raise ValueError("Script must be a list")
                 
            is_valid, error_msg = self._validate_script(script)
            if not is_valid:
                raise ValueError(f"Script validation failed: {error_msg}")
                
            print(f"Pollinations successfully generated {len(script)} segments")
            return script
        except Exception as e:
            print(f"Pollinations script generation failed: {e}")
            if 'response_text' in locals():
                print(f"Partial response: {response_text[:200]}")
            raise e

    async def generate_script(
        self, 
        text: str, 
        max_length: int = 12000,
        model: str = "nvidia/nemotron-3-super-120b-a12b:free",  # OpenRouter fallback model
        max_retries: int = 3
    ) -> List[Dict]:
        """
        Generate a podcast script using multiple AI providers (Gemini -> OpenRouter -> Pollinations).
        """
        
        # --- 1. TRY GEMINI FIRST (Primary) ---
        try:
            print("--- Generating podcast script with Gemini AI (Primary)...")
            script = await self.generate_script_gemini(text)
            
            # --- FINAL STEP: SYNCHRONIZE TEXT WITH AUDIO ---
            from src.audio import format_text_for_deepgram
            for segment in script:
                segment["text"] = format_text_for_deepgram(segment["text"])
            return script
        except Exception as e:
            print(f"WARNING: Gemini Script Generation Failed: {e}")
            print("--- Falling back to OpenRouter...")

        # --- 2. TRY OPENROUTER (Fallback) ---
        if self.api_key:
            print(f"--- Calling OpenRouter API ({model})...")
            last_error = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        wait_time = (2 ** attempt) + 1
                        print(f"--- Retry attempt {attempt + 1}/{max_retries} in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    
                    input_text = text[:max_length]
                    prompt = self._format_prompt(input_text)
                    
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an expert podcast script writer. You create engaging, conversational scripts in valid JSON format."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=3000,
                        timeout=30.0
                    )
                    
                    response_text = response.choices[0].message.content
                    print(f"SUCCESS: Received response from OpenRouter: {len(response_text)} characters")
                    
                    cleaned_text = self._clean_json_response(response_text)
                    script = json.loads(cleaned_text)
                    
                    is_valid, error_msg = self._validate_script(script)
                    if is_valid:
                        print(f"SUCCESS: Successfully parsed {len(script)} segments")
                        # Show a preview of the script
                        print("--- SCRIPT PREVIEW ---")
                        for i, seg in enumerate(script[:3]):
                            # Safe print for Windows terminals
                            safe_text = seg['text'][:70].encode('ascii', 'ignore').decode('ascii')
                            print(f"  [{i}] {seg['speaker']}: {safe_text}...")
                        if len(script) > 3:
                            print(f"  ... and {len(script) - 3} more segments.")
                        print("----------------------")
                        
                        # --- FINAL STEP: SYNCHRONIZE TEXT WITH AUDIO ---
                        from src.audio import format_text_for_deepgram
                        for segment in script:
                            segment["text"] = format_text_for_deepgram(segment["text"])
                        
                        return script
                    else:
                        print(f"WARNING: OpenRouter script validation failed: {error_msg}")
                    
                except Exception as e:
                    last_error = str(e)
                    print(f"OpenRouter attempt {attempt+1} failed: {e}")

        # --- 3. TRY POLLINATIONS (Ultimate Fallback) ---
        try:
            script = await self.generate_script_pollinations(text)
        except Exception as e:
            print(f"Pollinations script generation also failed: {e}")
            script = self._create_error_fallback("Generation Failed", "All AI providers failed. Please check your API keys.")

        # --- FINAL STEP: SYNCHRONIZE TEXT WITH AUDIO ---
        # We apply the same formatting to the text field that Deepgram uses 
        # to ensure the visual subtitles match the spoken audio perfectly.
        from src.audio import format_text_for_deepgram
        for segment in script:
            segment["text"] = format_text_for_deepgram(segment["text"])
            
        return script
        
    
    async def generate_audio(
        self, 
        script: List[Dict], 
        output_dir: str,
        provider: str = "deepgram",  # FORCED TO DEEPGRAM FOR PODCASTS
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """
        Generate audio files for each script segment.
        
        Args:
            script: List of script segments
            output_dir: Directory to save audio files
            provider: Audio provider ("elevenlabs" or "edge")
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of generated audio filenames
        """
        print(f"--- Generating podcast: {len(script)} segments...")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        tasks = []
        total_segments = len(script)
        
        for i, segment in enumerate(script):
            speaker = segment["speaker"]
            text = segment["text"]
            
            # Get host configuration
            host = self.hosts.get(speaker)
            if not host:
                print(f"Unknown speaker '{speaker}', using default")
                host = self.hosts["Jax"]
            
            # Generate filename
            filename = f"podcast_seg_{i:03d}_{speaker}.mp3"
            output_path = os.path.join(output_dir, filename)
            
            # Create audio generation task
            voice = host.voice
            current_voice_id = voice.elevenlabs_id
            if provider == "deepgram":
                current_voice_id = f"aura-2-{speaker.lower()}-en"
                
            task = generate_audio(
                text=text,
                output_path=output_path,
                voice_id=current_voice_id,
                stability=voice.stability,
                similarity_boost=voice.similarity_boost,
                style=voice.style,
                provider=provider,
                speaking_rate=voice.speaking_rate,
                is_podcast=True
            )
            tasks.append((task, i + 1, total_segments, speaker))
        
        # Generate audio with progress tracking
        results = []
        for task, segment_num, total, speaker in tasks:
            try:
                result = await task
                results.append(result)
                
                if progress_callback:
                    progress_callback(segment_num, total, speaker)
                else:
                    # Find the original segment to get the text
                    seg_text = script[segment_num-1]["text"] if segment_num <= len(script) else ""
                    safe_text = seg_text[:60].encode('ascii', 'ignore').decode('ascii')
                    print(f"SUCCESS: Generated segment {segment_num}/{total} ({speaker}): \"{safe_text}...\"")
                    
            except Exception as e:
                print(f"Error generating audio for segment {segment_num}: {e}")
                results.append(None)
        
        # Filter out failed generations and return basenames
        successful_files = [
            os.path.basename(p) for p in results if p is not None
        ]
        
        print(f"SUCCESS: Generated {len(successful_files)}/{total_segments} audio segments")
        return successful_files


# Convenience functions for backward compatibility
async def generate_podcast_script(text: str) -> List[Dict]:
    """Generate a podcast script (legacy interface)."""
    if not OPENROUTER_API_KEY:
        print("ERROR: Cannot generate podcast: OPENROUTER_API_KEY not configured")
        return _create_error_fallback(
            "Configuration Error",
            "OpenRouter API key is not set. Please add OPENROUTER_API_KEY to your .env file."
        )
    
    generator = PodcastGenerator(OPENROUTER_API_KEY)
    return await generator.generate_script(text)


async def generate_podcast_audio(script: List[Dict], output_dir: str) -> List[str]:
    """Generate podcast audio (legacy interface)."""
    if not OPENROUTER_API_KEY:
        print("WARNING: OPENROUTER_API_KEY not set, but proceeding with audio generation")
    
    generator = PodcastGenerator(OPENROUTER_API_KEY)
    return await generator.generate_audio(script, output_dir)