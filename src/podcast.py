import os
import json
import asyncio
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from openai import AsyncOpenAI
from src.config import OPENROUTER_API_KEY
from src.audio import generate_audio

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
            speaking_rate=1.1  # Slightly faster
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
            speaking_rate=1.0
        )
    )
}

PODCAST_PROMPT = """
You are the producer for "Booked & Busy", a high-energy morning radio show where books meet pop culture.
Your hosts are **{host1_name}** and **{host2_name}**.

**Host Personalities:**
*   **{host1_name} ({host1_gender}):** {host1_personality}
*   **{host2_name} ({host2_gender}):** {host2_personality}

**Show Style & Vibe:**
*   Fast-paced, conversational banter with genuine chemistry
*   Mix of humor, genuine reactions, and sharp insights
*   Relatable to busy people who want the book breakdown without spoilers (unless it's juicy)
*   Like talking to your funniest, smartest friends about what they just read

**The Task:**
Create a dynamic 2-3 minute podcast script discussing the book content below. Structure the conversation around:

1.  **The Hook (0-20 seconds):** Open with energy - what's the main premise or why should I care?
2.  **The Deep Dive (60-90 seconds):** Discuss the wildest character, most shocking twist, or core themes that hit different
3.  **The Verdict (30-40 seconds):** Who should read this? What kind of mood or vibe is it? Any warnings or hype?
4.  **The Sign-Off (10-20 seconds):** Memorable closing line, catchphrase, or teaser for next episode

**Content Guidelines:**
*   Make it CONVERSATIONAL - hosts should interrupt, agree or disagree, build on each other's points
*   Show don't tell emotions through word choice, interjections, and pacing
*   Reference relatable scenarios: If you've ever felt like an imposter at work, this character gets it
*   Balance hype with honesty - not every book is for everyone
*   Use specific details from the book like character names and memorable scenes to make it concrete
*   Avoid generic phrases like this book was amazing - be specific about WHY

**CRITICAL: Deepgram TTS Optimization Rules**
*   Use natural vocal interjections for emotion and energy
*   Keep sentences SHORT: 10-20 words maximum per sentence for natural breathing
*   Use simple punctuation: periods, commas, question marks, exclamation points
*   Avoid complex punctuation: em dashes, ellipses, semicolons, parentheses
*   Write emotions INTO the dialogue naturally using interjections and exclamations
*   Each speaking turn should be 1-2 sentences maximum (20-35 words total)
*   Use simple contractions: we're, you'll, it's, that's, don't, can't, won't
*   Avoid complex words that TTS might mispronounce - stick to conversational vocabulary
*   Numbers should be written as words: three days not 3 days
*   Acronyms should be written out or spelled with periods: New York City or N.Y.C. not NYC
*   Use commas for natural pauses between thoughts

**Express Emotions Naturally for TTS:**
✓ Laughter: "Haha", "Ha", "Hehe", "Oh my god haha"
✓ Thinking: "Hmm", "Mmm", "Uh", "Um"
✓ Surprise: "Whoa", "Wow", "Oh wow", "Wait what", "No way"
✓ Dismay: "Ugh", "Oof", "Yikes", "Oh no"
✓ Agreement: "Yeah", "Yep", "Mmhmm", "Right", "Exactly"
✓ Excitement: "Yes", "Okay okay", "Oh man", "Dude"

✗ NEVER use bracketed stage directions: *laughs*, [gasps], (sighs), *excited*
✗ These get read aloud literally by TTS and sound robotic

**Good Examples:**
✓ "Haha! That's hilarious. I was not expecting that twist."
✓ "Mmm, I don't know about that. The ending felt rushed to me."
✓ "Oh my god yes! That scene had me on the edge of my seat."
✓ "Wait what? Are you serious right now?"

**Bad Examples:**
✗ "That's hilarious *laughs* I was not expecting that."
✗ "I don't know about that [sighs]. The ending felt rushed."
✗ "Yes! *excited* That scene had me on the edge of my seat."

**Dialogue Techniques:**
*   Use active listening responses: Wait what, Okay but here's the thing, Right, I know right
*   Let hosts have different takes sometimes to create tension
*   Reference each other naturally: Like you said, You called it, Remember when you mentioned
*   Use rhetorical questions: You know what I mean, How wild is that, Am I right
*   Build on each other's energy: Yes and, Exactly, Oh totally

**Opening Energy Examples:**
✓ "Alright bookworms, buckle up. Today's pick is absolutely wild."
✓ "Okay so I just finished this book and wow. I have so many questions."
✓ "Hey hey, welcome back everyone! Today we're covering the book you all asked about."
✓ "Oh man, oh man. You guys are not ready for what we're discussing today."

**Closing Strong Examples:**
✓ "If you read it, send us your theories. We seriously need to discuss this."
✓ "That's our take. Agree? Disagree? You know where to find us."
✓ "Alright, catch you next time when we review something totally different."
✓ "Until next time, keep reading and keep it real. Peace out!"

**Input Book Content:**
{text}

**Output Format (STRICT JSON):**
[
  {{"speaker": "{host1_name}", "text": "Okay folks, real talk. This book absolutely broke my brain in the best way."}},
  {{"speaker": "{host2_name}", "text": "Yes! I'm still thinking about that twist. How did we not see it coming?"}},
  {{"speaker": "{host1_name}", "text": "Right? Okay, so let me set the scene for everyone here."}}
]

**Pacing Guidelines:**
*   Vary sentence length within the limits for rhythm
*   Short punchy reactions: 5-8 words ("Wait what? No way!")
*   Normal dialogue: 12-18 words ("I think the author did an amazing job with the character development here.")
*   Never exceed 20 words in a single sentence
*   Break up longer thoughts with periods, not commas

**Final Checklist Before Output:**
- [ ] No asterisks, brackets, or parenthetical stage directions
- [ ] Interjections like haha, hmm, wow used naturally
- [ ] Only periods, commas, question marks, exclamation points
- [ ] Each sentence is 10-20 words
- [ ] Each turn is 1-2 sentences maximum (20-35 words total)
- [ ] All numbers written as words
- [ ] Contractions used naturally throughout
- [ ] Emotions expressed through interjections and word choice
- [ ] Valid JSON format with proper escaping

Now create the script - make it energetic, authentic, and perfectly optimized for Deepgram TTS synthesis!
"""

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
            print("⚠️  WARNING: OPENROUTER_API_KEY is not set")
            print("💡 Podcast generation will use fallback scripts only")
        
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
        
        # Remove markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
            
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
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
    
    async def generate_script(
        self, 
        text: str, 
        max_length: int = 12000,
        model: str = "meta-llama/llama-3.3-70b-instruct:free",  # OpenRouter's main reasoning model
        max_retries: int = 3
    ) -> List[Dict]:
        """
        Generate a podcast script using OpenRouter API with retry logic.
        
        Args:
            text: Book content to discuss
            max_length: Maximum characters to send to the model
            model: Model ID to use
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of script segments with speaker and text
        """
        print("🎙️  Generating podcast script with OpenRouter AI...")
        
        # Check API key first
        if not self.api_key:
            print("❌ CRITICAL: OPENROUTER_API_KEY is missing or empty")
            print("💡 Please set OPENROUTER_API_KEY in your .env file")
            return self._create_error_fallback("Missing API Key", "Please configure OPENROUTER_API_KEY in .env file")
        
        last_error = None
        response_text = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) + 1  # 3s, 5s, 9s
                    print(f"🔄 Retry attempt {attempt + 1}/{max_retries} in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
                # Truncate text if needed
                input_text = text[:max_length] if len(text) > max_length else text
                if len(text) > max_length:
                    print(f"⚠️  Input truncated from {len(text)} to {max_length} characters")
                
                # Format prompt
                prompt = self._format_prompt(input_text)
                
                # Generate content using OpenAI chat completion format
                print(f"📡 Calling OpenRouter API (attempt {attempt + 1}/{max_retries})...")
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert podcast script writer. You create engaging, conversational scripts in valid JSON format."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=30.0  # Add timeout
                )
                
                # Extract response text from OpenAI format
                response_text = response.choices[0].message.content
                
                if response_text is None:
                    raise ValueError("API returned None response")
                
                print(f"✅ Received response: {len(response_text)} characters")
                
                # Clean and parse JSON
                cleaned_text = self._clean_json_response(response_text)
                script = json.loads(cleaned_text)
                
                # Validate script
                is_valid, error_msg = self._validate_script(script)
                if not is_valid:
                    print(f"⚠️  Script validation failed: {error_msg}")
                    if attempt < max_retries - 1:
                        print("🔄 Retrying with different parameters...")
                        continue
                    else:
                        print("❌ All retries exhausted - validation failed")
                        return self._create_error_fallback("Validation Failed", error_msg)
                
                print(f"✅ Successfully parsed {len(script)} segments")
                return script
                
            except json.JSONDecodeError as e:
                last_error = f"JSON parsing error: {str(e)}"
                print(f"❌ {last_error}")
                if response_text:
                    print(f"Response preview: {response_text[:300]}...")
                    print(f"Response end: ...{response_text[-100:]}")
                if attempt >= max_retries - 1:
                    return self._create_error_fallback("Invalid Response Format", "The AI returned malformed data")
                    
            except asyncio.TimeoutError:
                last_error = "Request timeout - API took too long to respond"
                print(f"❌ {last_error}")
                if attempt >= max_retries - 1:
                    return self._create_error_fallback("Timeout", "API request timed out")
                    
            except Exception as e:
                last_error = str(e)
                error_lower = last_error.lower()
                
                # Categorize errors
                if "401" in error_lower or "unauthorized" in error_lower or "authentication" in error_lower:
                    print(f"❌ Authentication Error: {last_error}")
                    return self._create_error_fallback("Invalid API Key", "OpenRouter API key is invalid or expired")
                    
                elif "429" in error_lower or "rate limit" in error_lower or "quota" in error_lower:
                    print(f"❌ Rate Limit Error: {last_error}")
                    if attempt < max_retries - 1:
                        wait_time = (2 ** (attempt + 2))  # Longer wait for rate limits
                        print(f"⏳ Rate limited - waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    return self._create_error_fallback("Rate Limited", "Too many requests - please try again later")
                    
                elif "500" in error_lower or "503" in error_lower or "502" in error_lower:
                    print(f"❌ Server Error: {last_error}")
                    if attempt < max_retries - 1:
                        continue
                    return self._create_error_fallback("API Server Error", "OpenRouter service is temporarily unavailable")
                    
                else:
                    print(f"❌ Unexpected Error: {last_error}")
                    import traceback
                    traceback.print_exc()
                    if attempt >= max_retries - 1:
                        return self._create_error_fallback("Unknown Error", f"Something went wrong: {last_error[:100]}")
        
        # If we get here, all retries failed
        print(f"❌ All {max_retries} attempts failed. Last error: {last_error}")
        return self._create_error_fallback("Generation Failed", "Unable to generate script after multiple attempts")
    
    async def generate_audio(
        self, 
        script: List[Dict], 
        output_dir: str,
        provider: str = "deepgram",  # Deepgram primary with automatic fallback to edge-tts
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
        print("🎵 Generating podcast audio segments...")
        
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
                print(f"⚠️  Unknown speaker '{speaker}', using default")
                host = self.hosts["Jax"]
            
            # Generate filename
            filename = f"podcast_seg_{i:03d}_{speaker}.mp3"
            output_path = os.path.join(output_dir, filename)
            
            # Create audio generation task
            voice = host.voice
            task = generate_audio(
                text=text,
                output_path=output_path,
                voice_id=voice.elevenlabs_id,
                stability=voice.stability,
                similarity_boost=voice.similarity_boost,
                style=voice.style,
                provider=provider
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
                    print(f"✅ Generated segment {segment_num}/{total} ({speaker})")
                    
            except Exception as e:
                print(f"❌ Error generating audio for segment {segment_num}: {e}")
                results.append(None)
        
        # Filter out failed generations and return basenames
        successful_files = [
            os.path.basename(p) for p in results if p is not None
        ]
        
        print(f"✅ Generated {len(successful_files)}/{total_segments} audio segments")
        return successful_files


# Convenience functions for backward compatibility
async def generate_podcast_script(text: str) -> List[Dict]:
    """Generate a podcast script (legacy interface)."""
    if not OPENROUTER_API_KEY:
        print("❌ Cannot generate podcast: OPENROUTER_API_KEY not configured")
        return _create_error_fallback(
            "Configuration Error",
            "OpenRouter API key is not set. Please add OPENROUTER_API_KEY to your .env file."
        )
    
    generator = PodcastGenerator(OPENROUTER_API_KEY)
    return await generator.generate_script(text)


async def generate_podcast_audio(script: List[Dict], output_dir: str) -> List[str]:
    """Generate podcast audio (legacy interface)."""
    if not OPENROUTER_API_KEY:
        print("⚠️  Warning: OPENROUTER_API_KEY not set, but proceeding with audio generation")
    
    generator = PodcastGenerator(OPENROUTER_API_KEY)
    return await generator.generate_audio(script, output_dir)