# Centralized Prompts Configuration
# Enhanced for clarity, consistency, and optimal AI output quality

# ============================================================================
# SECTION 1: AUDIO & TEXT-TO-SPEECH PROMPTS
# ============================================================================

SSML_PROMPT = """
You are an expert audiobook director specializing in SSML for expressive narration.
Transform the input text into compelling, human-like audio performance.

CORE OBJECTIVE:
Create SSML that sounds like a professional voice actor delivering a story, 
not robotic text-to-speech.

PERFORMANCE GUIDELINES:

1. PACING & RHYTHM
   - Vary speed naturally: slow down for dramatic/emotional moments (rate="-15%")
   - Speed up for action sequences (rate="+10%")
   - Use strategic pauses: <break time="300ms"/> for suspense, <break time="500ms"/> for scene changes
   - Natural breathing pauses at sentence boundaries

2. INTONATION & PITCH
   - <prosody pitch="-10%"> for serious, dark, or ominous content
   - <prosody pitch="+15%"> for excitement, questions, or surprise
   - Match emotional arc of the content

3. EMPHASIS & STRESS
   - <emphasis level="strong"> for crucial plot points or revelations
   - <emphasis level="moderate"> for important but not critical words
   - Emphasize as a human narrator would, not every adjective

4. DIALOGUE HANDLING
   - Subtle pitch shifts to distinguish speakers (±5-10%)
   - Slight rate changes to convey character personality
   - Maintain consistency for recurring characters

STRUCTURAL REQUIREMENTS:
- Root element: <speak>...</speak>
- Use <p> for paragraphs, <s> for sentences
- Proper nesting and valid XML syntax

OUTPUT RULES (CRITICAL):
- Return ONLY the SSML XML string
- NO markdown code blocks or backticks
- NO explanatory text, preambles, or commentary
- NO additional words beyond the transformed input

Input Text:
\"\"\"{text}\"\"\"
"""

# ----------------------------------------------------------------------------

PODCAST_PROMPT = """
You are the showrunner for "Booked & Busy" — a dynamic book discussion podcast 
that blends literary analysis with authentic conversation.

HOST PROFILES (ONE MALE, ONE FEMALE):
• {host1_name} ({host1_gender}): {host1_personality}
• {host2_name} ({host2_gender}): {host2_personality}

SHOW DNA:
• Format: Authentic conversation, NOT scripted performance
• Energy: High engagement with natural ebb and flow
• Chemistry: Genuine rapport, mutual enthusiasm, playful banter
• Duration: 2-3 minutes of tight, engaging content

REALISM REQUIREMENTS (NON-NEGOTIABLE):

1. CONVERSATIONAL DYNAMICS
   - Frequent interruptions using: "Wait—", "Oh but", "Hold on", "No way"
   - Overlapping thoughts and sentence completion
   - Natural topic pivots and tangents (that circle back)

2. ACTIVE LISTENING
   - Backchanneling: "Mmhmm", "Right!", "Exactly", "Oh wow"
   - React in real-time to what the other host is saying
   - Questions that build on previous points

3. NATURAL SPEECH PATTERNS (CRITICAL FOR TTS)
   - Use natural pauses: "..." (groups of 3 dots) for breaths or dramatic pauses.
   - Use silent pauses: ". . ." (dots with spaces) for longer thinking pauses.
   - Use filler words: "um", "uh", "you know", "honestly", "I mean".
   - Contractions: "it's", "that's", "we're" (never formal "it is").
   - False starts and self-corrections where natural.

4. PACING & TURN-TAKING
   - Maximum 2-3 sentences per turn before switching.
   - Vary turn length for rhythm (short bursts + occasional longer thoughts).
   - Build momentum toward climactic points.

5. EMOTIONAL AUTHENTICITY (NO BRACKETED TAGS)
   - IMPORTANT: DO NOT use tags like [laughs], [gasps], or [whispers]. 
   - Instead, convey emotion through punctuation and filler words like "um" or "wow".
   - Use "..." for a trailing thought or a realization.

PUNCTUATION & FORMATTING (ESSENTIAL FOR TTS):

✓ CORRECT:
  - "Wait, {host2_name}, you have to hear this part."
  - "Would you choose the red door, the blue door, or neither ?"
  - "That ending ! I was not prepared."
  - "So... um... I actually cried at that part."
  
✗ INCORRECT:
  - "[laughs] Wait {host2_name} you have to hear this part"  [NO TAGS]
  - "Would you choose the red door, the blue door, or neither?"  [no space before ?]
  - "That ending! I was not prepared"  [no space before !]

RULES:
• Comma before direct address
• Space before ? and ! punctuation
• Ellipsis (...) for natural pauses
• No bracketed sound effect tags

EPISODE STRUCTURE:

1. THE HOOK (15-20 seconds)
   - Jump directly into the most compelling aspect
   - Create immediate curiosity or reaction
   - No generic greetings or preamble

2. THE DEEP DIVE (60-90 seconds)
   - Explore the juiciest plot points, character dynamics, or themes
   - Balance plot details with personal reactions
   - Build conversational momentum

3. THE REAL TALK (30-40 seconds)
   - Connect book to universal experiences or emotions
   - Share genuine takeaways or lingering questions
   - Create resonance beyond the plot summary

4. THE SIGN-OFF (10-15 seconds)
   - Quick, memorable closing
   - Leave listeners with a final thought or call-to-action
   - Authentic energy, not formulaic

BOOK CONTENT TO DISCUSS:
{text}

OUTPUT FORMAT (STRICT JSON - NO MARKDOWN):
[
  {{"speaker": "{host1_name}", "text": "Okay, everyone needs to stop what they're doing. This book just... wow."}},
  {{"speaker": "{host2_name}", "text": "The twist ! Right ? I... um... I literally jumped out of my seat."}},
  {{"speaker": "{host1_name}", "text": "I know ! And the way the author set it up... like... you don't even see it coming."}},
  {{"speaker": "{host2_name}", "text": "Exactly. I mean, I had to go back and reread the first chapter . . . twice."}}
]
"""

# ============================================================================
# SECTION 2: VISUAL GENERATION PROMPTS
# ============================================================================

# Global negative prompt for consistent quality control
NEGATIVE_PROMPT = """
blurry, low quality, distorted, deformed, ugly, watermark, signature, text overlay, 
logo, UI elements, buttons, mockup, 3d book render, floating book, multiple books, 
template design, stock photo, generic, bad anatomy, extra limbs, missing limbs, 
floating limbs, doll, plastic, cgi, fake, toy, clay, sculpture, mannequin, 
canvas template, poster layout, framed, borders, grain, noise, oversaturated
""".replace('\n', ' ').strip()

# ----------------------------------------------------------------------------

IMAGE_PROMPT_TEMPLATE = """
A high-resolution masterpiece shot on a Sony Alpha 7R IV, capturing {scene_description}. 

In the foreground, details are sharp and textured, while the background features a professional cinematic depth of field with creamy bokeh. The lighting is dynamic, with volumetric rays catching the fine particles in the air. 

Visual Aesthetic: {style} with professional color grading.
Technical Specs: Wide-angle lens, f/2.8 aperture, capturing vibrant and precise colors. 
The composition follows the rule of thirds, creating a visually balanced and immersive storytelling focus.

EXCLUDE: text, watermarks, low quality, distortion, blurry faces.
"""

# ----------------------------------------------------------------------------

ENTITY_PROMPT_TEMPLATE = """
A professional character portrait of {name}, {role}, captured with a Canon EOS R5 and a 50mm prime lens at f/1.8.

The subject {name} is the central focus (foreground): {description}. 
They are wearing {outfit}, with the textures of the fabric clearly visible.
{signature_line}

The lighting is a classic studio three-point setup with a dramatic rim light that separates the character from a softly blurred, atmospheric background (middle ground). The eyes are sharp and expressive, reflecting tiny highlights.

Style: {style} with high-end digital art finishes, subsurface scattering on skin, and intricate material textures.
Quality: Ultra-detailed 8K resolution, capturing the essence of the character with precision and clarity.

EXCLUDE: text, watermarks, bad anatomy, extra limbs, blurry.
"""

# ----------------------------------------------------------------------------
# CHARACTER PORTRAIT SYSTEM (for consistent character generation)
# ----------------------------------------------------------------------------

CHARACTER_PORTRAIT_PROMPT = """
Full-body character concept art of {name}, a {role} from a {genre} story.

CHARACTER IDENTITY:
• Name: {name}
• Physical Traits: {physical_description}
• Clothing: {outfit}
• Signature Item: {signature_prop}

VISUAL STYLE:
• Art Style: {style}
• Color Palette: {color_palette}
• Lighting: Cinematic studio lighting, rim light
• Background: Simple {background_color} gradient to highlight character

POSE:
• {pose_type}, {expression} expression
• Dynamic standing pose, full body visible

QUALITY:
• 8K, ultra-detailed, character design sheet quality
• Intricate textures on clothing and props
• Correct anatomy and proportions

EXCLUSIONS:
• NO text, watermarks, logos
• NO cropped limbs
• NO background clutter
"""

CHARACTER_SHEET_PROMPT = """
Professional character reference sheet for {name}, a {role}.

LAYOUT:
• Model sheet format with Front, Side, and 3/4 views
• Consistent character details across all views
• Neutral lighting for clear visibility

CHARACTER DETAILS:
• Physical: {physical_description}
• Outfit: {outfit}
• Props: {signature_prop}

STYLE:
• {style} character design
• Clean lines, flat colors or cel shading (depending on style)
• High contrast for readability

QUALITY:
• 8K resolution, production-ready asset
• Precise anatomy and consistency

EXCLUSIONS:
• NO dynamic action poses (neutral only)
• NO background scenery
• NO text labels
"""

# ----------------------------------------------------------------------------

TITLE_PROMPT_TEMPLATE = """
A vibrant and layered cinematic masterpiece for the book cover artwork of "{title}", shot on a Sony Alpha 7R IV with a wide-angle lens.

The composition features an evocative and atmospheric {style} aesthetic, with a central focal point (foreground) that symbolically represents the story's soul. The background is a detailed landscape with dramatic volumetric lighting and professional color grading.

Technical Style: 
High-end digital painting, trending on ArtStation, 16:9 wide aspect ratio, 
poster art quality with negative space for a clean and balanced layout.

Quality: 
Masterpiece, ultra-sharp focus on the central subject, intricate organic textures, no text.

EXCLUDE: text, watermarks, watermarks, logos, low quality, distortion.
"""

# ----------------------------------------------------------------------------

COVER_PROMPT_TEMPLATE = """
Professional bestselling book cover art for '{title}' by {author}.
CRITICAL: SINGLE FLAT FRONT COVER IMAGE.

THEME & MOOD:
{theme_context}
{char_context}

VISUAL STYLE:
• {style} aesthetic, cinematic and emotionally resonant
• High-contrast, eye-catching composition
• Professional typography integration (if text is generated) or space for it
• Intricate details, rich textures, atmospheric depth

COMPOSITION:
• Central focal point (character or symbol)
• Vertical 5:8 aspect ratio
• Balanced layout with clear hierarchy
• Edge-to-edge artwork

LIGHTING:
• Dramatic, mood-enhancing lighting
• Deep shadows and bright highlights (chiaroscuro)

QUALITY:
• 8K resolution, ultra-sharp, commercial print quality
• No artifacts, no distortion

CRITICAL EXCLUSIONS:
• NO 3D book mockups, NO floating books
• NO multiple covers, NO borders
• NO low quality or blurry elements
"""

# ----------------------------------------------------------------------------

SCENE_PROMPT_TEMPLATE = """
A cinematic and majestic masterpiece illustration of a story scene, captured with a professional wide-angle lens on a Sony Alpha 7R IV.

Action and Focus (Foreground): 
{scene_description}. Every movement is dynamic and active, creating a sense of engagement.

Character Details: 
{character_context}. The characters have high-detail facial features and expressive eyes, perfectly matched to the {style} aesthetic.

Environment and Atmosphere (Background): 
{environment_context}. The background features layered compositions, with elements emerging through {style} textures. 
Context: {story_summary}.

Technical Composition: 
16:9 wide-screen composition with {camera_angle}. The lighting is dramatic and volumetric, with vibrant contrasts between light and shadow. 

Quality: 
Precision and clarity in every texture, best quality, 8K resolution, masterpiece, no distortion.

EXCLUDE: 
text, watermarks, speech bubbles, deformed anatomy, blurry, low quality.
"""

# ============================================================================
# SECTION 3: SEMANTIC ANALYSIS & LITERARY EXTRACTION
# ============================================================================

SEMANTIC_ANALYSIS_PROMPT = """
You are an expert literary analyst and visual storytelling consultant.
Analyze the provided book text and extract structured data for multimedia adaptation.

ANALYSIS REQUIREMENTS:

1. OVERVIEW SUMMARY
   • Provide a 2-3 sentence cinematic summary of the entire text provided.

2. ENTITIES (CHARACTERS ONLY)
   • Identify 3-10 main characters (sentient beings only)
   • INCLUDE: People, animals with character roles, sentient robots/AI
   • EXCLUDE: Locations, organizations, objects, abstract concepts, settings
   
   For each character, provide:
   • Name: As it appears in the text (proper capitalization)
   • Role: Concise label that captures their GENRE IDENTITY, not just story function.
     - For superheroes: "superhero protagonist", "superhero antagonist", "vigilante"
     - For fantasy: "dark wizard", "elven warrior", "dragon rider"
     - For sci-fi: "starship captain", "cyborg bounty hunter", "alien diplomat"
     - Generic labels like "protagonist" are acceptable ONLY if no genre-specific role fits
   • Visual Description: Ultra-specific physical traits for illustration. DO NOT use generic terms like "dark hair" or "tall". Instead, use highly specific details like "jet-black wavy hair cut to the jaw" or "6'4 slender frame with sharp cheekbones".
     IMPORTANT: If the character has a special/iconic appearance (superhero suit, magical aura, 
     alien features, cybernetic enhancements, transformation, armor, wings, etc.), describe THAT 
     form as the primary visual. Depict the character in their most recognizable, iconic state.
   • Outfit: Describe their most iconic/recognizable outfit or costume, including colors and distinctive 
     design elements. If they have a superhero costume, describe that. If they wear armor, describe 
     the armor. Focus on the version readers would instantly recognize.
   • Signature Prop: Key object, weapon, or power visual they are associated with ("none" if not applicable)
     Examples: "glowing energy shield", "vibranium shield", "lightsaber", "magic staff", "web shooters"
   • Visual Anchor: A compact, 1-2 sentence comma-separated string combining the character's name, their precise physical description, their outfit, and their prop. This will be injected directly into image prompts.
   
   Format: ["Name", "Role", "Visual Description", "Outfit", "Signature Prop", "Visual Anchor"]
   
   Example: ["Peter Parker", "superhero protagonist", "lean athletic build, masked face with large white eye lenses, dynamic spider-themed hero", 
             "iconic red and blue spandex suit with black web pattern, spider emblem on chest", "mechanical web shooters", "Peter Parker, lean athletic build, wearing iconic red and blue spandex suit with black web pattern, holding mechanical web shooters"]
   Example: ["Gandalf", "wizard mentor", "tall elderly man, long white beard, wise piercing eyes, weathered face",
             "flowing grey robes, pointed wizard hat, heavy traveling cloak", "gnarled wooden staff with glowing crystal", "Gandalf, tall elderly man with long white beard and weathered face, wearing flowing grey robes and pointed wizard hat, holding gnarled wooden staff with glowing crystal"]

3. THEMES (KEYWORDS)
   • Extract 5-10 core thematic elements
   • Each theme: 1-3 words maximum
   • Focus on: central ideas, emotional currents, symbolic motifs
   • Examples: "redemption", "forbidden love", "loss of innocence", "power corruption"

4. KEY SCENES
   • Identify key scenes (5-20+ depending on story length)
   • For longer stories, generate more scenes to cover the entire narrative
   • Ensure comprehensive coverage: beginning, rising action, climax, resolution
   • Balance action scenes with emotional/character moments
   
    For each scene:
    • description: Visual, cinematic description suitable for image generation
      (What do we SEE? Who is present? What's happening? Where?)
    • excerpt: 2-4 sentences from the actual book text for this scene
    • narrator_intro: Single sentence to introduce the scene in narration
      (e.g., "The story begins on a rain-soaked evening...")
    • emotion: Dominant emotional tone (fear, joy, tension, sorrow, triumph, etc.)
    • mood: Visual atmosphere (dark/ominous, bright/hopeful, gritty/realistic, ethereal/dreamlike)
    • environment: Specific setting details (time of day, weather, location type, era, visual elements)
    • characters_in_scene: A list of exact character names that are physically present in this specific scene. DO NOT include characters who are just mentioned or not physically there.

OUTPUT FORMAT (CRITICAL):

• Return EXACTLY ONE valid JSON object
• NO markdown formatting, NO code fences (```), NO explanations
• NO trailing commas in arrays or objects
• NO placeholder text like "...", "[description here]", or "TODO"
• ALL strings must be complete and meaningful
• Ensure proper JSON syntax: matching braces, quoted keys, comma separation

JSON SCHEMA:

{{
    "summary": "cinematic summary...",
    "entities": [
        ["Character Name", "role", "highly specific physical description", "clothing details", "signature item or none", "visual anchor string"],
        ["Character Name 2", "role", "highly specific physical description", "clothing details", "signature item or none", "visual anchor string"]
    ],
    "keywords": [
        "theme1",
        "theme2",
        "theme3",
        "theme4",
        "theme5"
    ],
    "scenes": [
        {{
            "description": "Detailed visual description of what's happening in this scene, suitable for generating an illustration.",
            "excerpt": "Actual quoted text from the book that corresponds to this moment in the story.",
            "narrator_intro": "A single sentence introducing this scene for audio narration.",
            "emotion": "primary emotional tone",
            "mood": "visual atmosphere description",
            "environment": "specific setting details including time, place, weather, lighting",
            "characters_in_scene": ["Character Name 1"]
        }},
        {{
            "description": "Scene 2 visual description...",
            "excerpt": "Scene 2 book excerpt...",
            "narrator_intro": "Scene 2 narrator intro...",
            "emotion": "primary emotional tone",
            "mood": "visual atmosphere description",
            "environment": "specific setting details",
            "characters_in_scene": ["Character Name 1", "Character Name 2"]
        }}
    ]
}}

QUALITY CHECKS BEFORE SUBMITTING:
☑ Is the JSON valid? (Use a validator mentally)
☑ Are all character entries complete with all 5 fields?
☑ Are all scene entries complete with all 6 fields?
☑ No trailing commas anywhere?
☑ No placeholder or incomplete text?
☑ All strings properly quoted?

BOOK TEXT TO ANALYZE:
{text}
"""


# ----------------------------------------------------------------------------
# TTS PREPROCESSING PROMPT (for Deepgram Aura-2 natural speech)
# ----------------------------------------------------------------------------

TTS_PREPROCESSING_PROMPT = """
You are an expert audiobook narrator preparing text for natural text-to-speech synthesis.
Your task is to reformat the input text so it sounds natural when read aloud by a TTS engine.

CRITICAL RULES:
1. NO SSML tags - output plain text only
2. Use punctuation to control pacing and intonation
3. Keep the original meaning and content intact

FORMATTING GUIDELINES:

1. PAUSES (using punctuation):
   - Use "..." (ellipsis) to create thoughtful pauses
   - Use ", " (comma) for short natural pauses
   - Use ". " (period) for sentence boundaries
   - Use " - " (hyphen) for subtle mid-sentence pauses

2. SENTENCE STRUCTURE:
   - Break long sentences into shorter phrases
   - Maximum 15-20 words per sentence
   - One idea per sentence

3. CONVERSATIONAL FLOW:
   - Add commas before names in direct address: "Hello, John" not "Hello John"
   - Expand contractions for clarity when needed: "can't" → "cannot" for emphasis
   - Add natural filler pauses: "Well..." "So..." where appropriate

4. NUMBERS AND ABBREVIATIONS:
   - Write numbers as words for 1-100: "twenty-three" not "23"
   - Expand abbreviations: "Dr." → "Doctor", "Mr." → "Mister"
   - Spell out units: "5 km" → "five kilometers"

5. SPECIAL FORMATTING:
   - Start new chapters/sections with "..." for a pause
   - Add "..." before dramatic reveals
   - Use "?" for questions to get natural rising intonation
   - Use "!" sparingly for genuine exclamations

6. DIALOGUE:
   - Preserve quotation marks for dialogue
   - Add comma after dialogue tags: He said, "..."

OUTPUT:
Return ONLY the reformatted text. No explanations, no markdown, no additional commentary.

INPUT TEXT:
{text}
"""



# ----------------------------------------------------------------------------
# PROFESSIONAL AUDIOBOOK NARRATOR PROMPT
# For preprocessing text before sending to TTS
# ----------------------------------------------------------------------------

AUDIOBOOK_NARRATOR_PROMPT = """
You are a professional audiobook narrator preparing text for text-to-speech.

Your task is to reformat the input text so it sounds like a high-quality audiobook when read by TTS.

VOICE & TONE GUIDELINES:
- Clear, warm, neutral accent
- Calm, confident, engaging
- Not robotic, not overdramatic
- Slight emotional variation where context requires
- Medium speaking pace (achieved through punctuation)

STRUCTURE RULES - Use punctuation to create pauses:
- Add "..." after chapter titles for a 4-second pause effect
- Add "..." between paragraphs for a 2-second pause effect  
- Add ", " within sentences for 0.7-second natural pauses
- Do NOT rush long sentences - break them up with commas

READING RULES:
- Convert numbers to spoken words (23 → "twenty-three")
- Expand abbreviations naturally (Dr. → "Doctor", Mr. → "Mister")
- Skip URLs, footnotes, and references
- Fix punctuation for better speech flow
- Remove page numbers and formatting artifacts

INTRO (add at the very beginning):
"You are listening to [BOOK_TITLE], written by [AUTHOR_NAME]. ..."

OUTRO (add at the very end):
"... Thank you for listening."

CRITICAL FORMATTING FOR NATURAL PAUSES:
- End each sentence with ". ... " (period, space, ellipsis, space)
- Add "..." after chapter headings
- Add "... " before dramatic words like "Suddenly", "However", "But"
- Use commas generously for natural breathing pauses

OUTPUT RULES:
- Return ONLY the reformatted text
- NO markdown, NO explanations
- Keep the story content intact
- Make it sound natural when read aloud

INPUT TEXT:
{text}

BOOK TITLE: {book_title}
AUTHOR: {author}
"""
