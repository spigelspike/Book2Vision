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

HOST PROFILES:
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

3. NATURAL SPEECH PATTERNS
   - Occasional fillers: "like", "you know", "I mean", "honestly" (use sparingly)
   - Contractions: "it's", "that's", "we're" (never formal "it is")
   - False starts and self-corrections where natural

4. PACING & TURN-TAKING
   - Maximum 2-3 sentences per turn before switching
   - Vary turn length for rhythm (short bursts + occasional longer thoughts)
   - Build momentum toward climactic points

5. EMOTIONAL AUTHENTICITY
   - Express genuine reactions: [laughs], [gasps], [whispers], [excitedly]
   - Vary energy levels throughout the conversation
   - Show vulnerability and personal connection to material

PUNCTUATION & FORMATTING (ESSENTIAL FOR TTS):

✓ CORRECT:
  - "Wait, {host2_name}, you have to hear this part."
  - "Would you choose the red door, the blue door, or neither ?"
  - "That ending ! I was not prepared."
  
✗ INCORRECT:
  - "Wait {host2_name} you have to hear this part"  [missing commas]
  - "Would you choose the red door, the blue door, or neither?"  [no space before ?]
  - "That ending! I was not prepared"  [no space before !]

RULES:
• Comma before direct address
• Space before ? and ! punctuation
• Periods for natural pauses between thoughts
• Commas for list items and clause separation

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
  {{"speaker": "{host1_name}", "text": "Okay, everyone needs to stop what they're doing. This book just—"}},
  {{"speaker": "{host2_name}", "text": "The twist ! Right ? I literally gasped out loud."}},
  {{"speaker": "{host1_name}", "text": "I know ! And the way the author set it up, like, you don't even see it coming."}},
  {{"speaker": "{host2_name}", "text": "Exactly. I mean, I had to go back and reread the first chapter."}}
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
Cinematic {style} masterpiece: {scene_description}.

Visual Style: 
High-end {style} aesthetic, trending on ArtStation, 8K resolution, 
ultra-detailed, professional color grading, dramatic lighting.

Composition: 
Dynamic framing, rule of thirds, depth of field, visual storytelling focus.

Atmosphere: 
Immersive, textured, volumetric lighting, ray tracing, particle effects.

Quality Markers: 
Award-winning photography, sharp focus, intricate details, organic textures.

EXCLUDE: Text, watermarks, logos, UI elements, low quality, distortion.
"""

# ----------------------------------------------------------------------------

ENTITY_PROMPT_TEMPLATE = """
Cinematic character portrait of {name}, {role}.

SUBJECT:
{name} — {description}
Wearing: {outfit}
{signature_line}

COMPOSITION:
Head and upper body portrait, slight three-quarter angle, looking at or near the viewer.
Shallow depth of field with creamy bokeh background.
Dramatic rim lighting from behind, soft key light from the front.

VISUAL STYLE:
{style}, highly detailed, expressive face with clear emotions,
subsurface scattering on skin, intricate fabric and material textures,
cinematic color grading, professional studio portrait quality.

QUALITY:
8K resolution, masterpiece, best quality, sharp focus on eyes and face,
award-winning character design, trending on ArtStation.

EXCLUDE: Text, watermarks, deformed anatomy, extra fingers, blurry, low quality, multiple people.
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
Cinematic book cover artwork for "{title}".

Visual Style: 
{style}, evocative and atmospheric, highly detailed digital painting, 
poster art quality, trending on ArtStation.

Subject: 
Symbolic representation of the title, atmospheric scene, no text.

Composition: 
16:9 aspect ratio, wide shot, negative space for potential text placement, 
balanced and epic.

Lighting: 
Dramatic, moody, volumetric fog, cinematic color grading.

Quality: 
Masterpiece, 8K, sharp focus, intricate details.

EXCLUDE: Any text, watermarks, generic stock imagery, book mockups.
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
Cinematic {style} illustration of a story scene.

ACTION: 
{scene_description}

CONTEXT: 
{story_summary}

ENVIRONMENT: 
{environment_context}
Detailed background, atmospheric, immersive.

CHARACTERS: 
{character_context}
(Ensure consistent appearance: {style})

CAMERA: 
{camera_angle}, dynamic composition, cinematic depth of field.

VISUAL STYLE: 
{style}, high-end digital art, detailed textures, dramatic lighting, 
color graded for mood.

QUALITY: 
Masterpiece, 8K, best quality, trending on ArtStation.

EXCLUDE: 
Speech bubbles, text, comic panels (unless specified), low quality, 
deformed characters, inconsistencies.
"""

# ============================================================================
# SECTION 3: SEMANTIC ANALYSIS & LITERARY EXTRACTION
# ============================================================================

SEMANTIC_ANALYSIS_PROMPT = """
You are an expert literary analyst and visual storytelling consultant.
Analyze the provided book text and extract structured data for multimedia adaptation.

ANALYSIS REQUIREMENTS:


2. ENTITIES (CHARACTERS ONLY)
   • Identify 3-10 main characters (sentient beings only)
   • INCLUDE: People, animals with character roles, sentient robots/AI
   • EXCLUDE: Locations, organizations, objects, abstract concepts, settings
   
   For each character, provide:
   • Name: As it appears in the text (proper capitalization)
   • Role: Concise label (e.g., "protagonist", "antagonist", "mentor", "ally")
   • Visual Description: Physical traits for illustration (age, build, hair, distinctive features)
   • Outfit: Specific clothing details (colors, style, condition, era)
   • Signature Prop: Key object they carry/use ("none" if not applicable)
   
   Format: ["Name", "Role", "Visual Description", "Outfit", "Signature Prop"]
   
   Example: ["Sarah Chen", "protagonist", "athletic build, short black hair, determined eyes", 
             "worn leather jacket, dark jeans, combat boots", "silver compass necklace"]

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

OUTPUT FORMAT (CRITICAL):

• Return EXACTLY ONE valid JSON object
• NO markdown formatting, NO code fences (```), NO explanations
• NO trailing commas in arrays or objects
• NO placeholder text like "...", "[description here]", or "TODO"
• ALL strings must be complete and meaningful
• Ensure proper JSON syntax: matching braces, quoted keys, comma separation

JSON SCHEMA:

}}
    "entities": [
        ["Character Name", "role", "physical description", "clothing details", "signature item or none"],
        ["Character Name 2", "role", "physical description", "clothing details", "signature item or none"]
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
            "environment": "specific setting details including time, place, weather, lighting"
        }},
        {{
            "description": "Scene 2 visual description...",
            "excerpt": "Scene 2 book excerpt...",
            "narrator_intro": "Scene 2 narrator intro...",
            "emotion": "primary emotional tone",
            "mood": "visual atmosphere description",
            "environment": "specific setting details"
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
