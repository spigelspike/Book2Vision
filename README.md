# 📚 Book2Vision

<p align="center">
  <img src="web/assets/hero.png" alt="Book2Vision Hero Banner" width="100%" />
</p>

<p align="center">
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python Version" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Framework-FastAPI-009688.svg" alt="FastAPI" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/AI%20Engine-Google%20Gemini-4285F4.svg" alt="Google Gemini" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Audio-ElevenLabs%20%7C%20Deepgram-ff69b4.svg" alt="Audio Providers" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Visuals-DeAPI%20%7C%20Pollinations-orange.svg" alt="Visual Generators" /></a>
  <a href="#-license"><img src="https://img.shields.io/badge/License-Educational-green.svg" alt="License" /></a>
</p>

---

## 🌟 Overview

**Book2Vision** is an AI-powered multimedia transformation platform designed to turn traditional books (PDF, EPUB, TXT) into rich visual, auditory, and interactive digital experiences. 

By integrating Large Language Models, Multi-Provider Speech Synthesis, and Diffusion Image/Video engines, Book2Vision converts static literature into custom audiobooks, character art portraits, key scene galleries, multi-speaker conversational podcasts, animated video summaries, page-by-page illustrated storybooks, and intelligent Q&A study assistants.

---

## 🎯 Dual-Mode Experience

<p align="center">
  <img src="web/assets/dual_mode.png" alt="Book2Vision Story Mode vs Study Mode" width="100%" />
</p>

Book2Vision offers two tailored consumption modes depending on user intent:

| Feature | 📖 Story Mode | 🎓 Study Mode |
| :--- | :--- | :--- |
| **Primary Goal** | Immersion, narrative enjoyment, visual storytelling | Comprehension, deep academic analysis, quick research |
| **Audio Generation** | Multi-speaker emotive audiobooks & narrative podcasts | Key takeaway narration & audio concept summaries |
| **Visual Art** | Scene galleries, character art portraits & video clips | Concept relationship graphs & structural mind maps |
| **Interactivity** | Page-by-page illustrated storybook view | Context-aware Q&A chatbot & interactive quizzes |
| **Target Content** | Fiction, novels, memoirs, fantasy, drama | Non-fiction, textbooks, research papers, documentation |

---

## 🚀 Key Features

- **📄 Multi-Format Document Ingestion**: Ingests PDF, EPUB, and TXT files. Handles scanned documents automatically via Tesseract OCR and Gemini 1.5 Flash layout-aware vision parsing with OCR.space fallback.
- **🧠 Semantic Narrative Engine**: Uses Google Gemini to extract characters, key scene settings, narrative arcs, loglines, themes, and key takeaways using a smart full-book text sampler (`create_book_digest`).
- **🎙️ Multi-Provider Audio Synthesis**: Generates natural speech using ElevenLabs, Deepgram (with automatic 2,000-character payload chunking), Edge-TTS (inbuilt free neural voices), and Pollinations TTS. Includes SSML enhancement and database caching.
- **🖼️ AI Character & Scene Art**: Generates character portraits and key scene illustrations using DeAPI (Flux model) with automatic fallback to Pollinations AI.
- **🎙️ Conversational AI Podcasts**: Generates multi-speaker podcast scripts using DeepSeek or Gemini, synthesizing conversational host episodes discussing story arcs or study themes.
- **🎬 Animated Video Summaries**: Produces video highlights using LTX-2 19B and CogVideoX models from generated illustrations.
- **📖 Page-by-Page Illustrated Storybook**: Adapts books into an illustrated reading mode matching text blocks with visual scene artwork.
- **💬 Intelligent Q&A Chatbot**: Ask questions directly about the uploaded book with instant context-backed answers and quizzes.
- **💾 Persistent Library & ZIP Export**: Database-backed book storage (SQLite / SQLModel & Supabase sync) with metadata, cover reloading, and one-click ZIP package exports.

---

## 🏗️ System Architecture & Data Flow

Below is the verified system flowchart based on deep codebase analysis across ingestion, semantic extraction, visual/audio dispatching, storage, and frontend presentation:

```mermaid
graph TD
    classDef userAccess fill:#6b4ce6,stroke:#fff,stroke-width:2px,color:#fff,rx:8px
    classDef process fill:#2a2a35,stroke:#4a4a5a,stroke-width:2px,color:#e1e1e6,rx:8px
    classDef ai fill:#00b8d9,stroke:#fff,stroke-width:2px,color:#000,rx:8px
    classDef storage fill:#36b37e,stroke:#fff,stroke-width:2px,color:#000,rx:8px
    classDef frontend fill:#ffab00,stroke:#fff,stroke-width:2px,color:#000,rx:8px

    %% --- Input & Ingestion Phase ---
    User((User / Browser)):::userAccess -->|Upload File| UploadAPI["/api/upload (FastAPI Router)"]:::process
    User -->|Select Saved Book| LibraryAPI["/api/library/load"]:::process

    UploadAPI --> FileValidation["Validate MIME & Size (<50MB)"]:::process
    FileValidation --> IngestionEngine["ingest_book() (src/ingestion.py)"]:::process
    
    IngestionEngine -->|PDF Native| PyPDF2Parser["PyPDF2 Reader"]:::process
    PyPDF2Parser -- Scanned / <100 chars --> GeminiVision["Gemini 1.5 Flash Vision"]:::ai
    GeminiVision -- API Error / 429 --> OCRSpace["OCR.space Fallback API"]:::ai
    
    IngestionEngine -->|EPUB| EbookLibParser["EbookLib + BeautifulSoup4"]:::process
    IngestionEngine -->|TXT| TxtParser["UTF-8 Text Reader"]:::process

    PyPDF2Parser --> TextDigest["create_book_digest() (src/text_sampler.py)"]:::process
    GeminiVision --> TextDigest
    OCRSpace --> TextDigest
    EbookLibParser --> TextDigest
    TxtParser --> TextDigest

    %% --- Semantic Analysis Phase ---
    TextDigest --> SemanticAnalysis["semantic_analysis() (src/analysis.py)"]:::process
    SemanticAnalysis -->|Multi-Key Rotation| GeminiLLM["Google Gemini (Flash/Pro)"]:::ai
    GeminiLLM -.->|Structured JSON| SemanticAnalysis
    
    SemanticAnalysis --> ExtractedData{"Extracted Analysis"}:::storage
    ExtractedData --> Entities["Entities (Name, Role, Outfit, Prop)"]
    ExtractedData --> Scenes["Scenes (Setting, Mood, Visual Prompt)"]
    ExtractedData --> BookSummary["Logline, Summary, Themes, Takeaways"]

    ExtractedData --> DB[(SQLite / SQLModel & Supabase)]:::storage
    LibraryAPI --> DB

    %% --- Visual Generation Phase ---
    UploadAPI -->|Background Task| BackgroundCover["generate_cover_background()"]:::process
    BackgroundCover --> CoverGen["generate_poster_with_deapi()"]:::process
    BackgroundCover --> EntityGen["generate_entity_image()"]:::process

    CoverGen --> DeAPI1{"DeAPI (Flux)"}:::ai
    DeAPI1 -- Primary Success --> ImageStore["/assets/visuals/ & /assets/entities/"]:::storage
    DeAPI1 -- Key Failure / 401 --> Pollinations1{"Pollinations AI"}:::ai
    Pollinations1 --> ImageStore

    EntityGen --> Pollinations2{"Pollinations AI"}:::ai
    Pollinations2 --> ImageStore

    %% --- Audio & Podcast Phase ---
    User -->|Select Audio Provider| AudioAPI["/api/generate/audio"]:::process
    AudioAPI --> SSMLGen["generate_ssml() (src/audio.py)"]:::process
    SSMLGen -->|Cache Lookup| DBCache{"Chapter Cache Hit?"}:::storage
    DBCache -- Yes --> TTSDispatch["generate_tts_audio()"]:::process
    DBCache -- No --> GeminiSSML["Gemini SSML Rewriter"]:::ai
    GeminiSSML --> TTSDispatch

    TTSDispatch --> ProviderCheck{"Check Provider"}:::process
    ProviderCheck -->|ElevenLabs| ElevenLabs["ElevenLabs API"]:::ai
    ProviderCheck -->|Deepgram| Deepgram["Deepgram Aura-2 (2k Chunks)"]:::ai
    ProviderCheck -->|Edge-TTS| EdgeTTS["Edge-TTS (Inbuilt Free)"]:::ai
    ProviderCheck -->|Pollinations| PollinationsTTS["Pollinations TTS API"]:::ai

    ElevenLabs --> AudioStore["/assets/audio/"]:::storage
    Deepgram --> AudioStore
    EdgeTTS --> AudioStore
    PollinationsTTS --> AudioStore

    %% --- Advanced Media & Content ---
    User -->|Request Podcast| PodcastAPI["/api/content/podcast"]:::process
    PodcastAPI --> PodcastScript["generate_podcast_script() (src/podcast.py)"]:::process
    PodcastScript --> DeepSeek["DeepSeek / Gemini LLM"]:::ai
    DeepSeek --> PodcastTTS["Multi-Speaker Audio Stitcher"]:::process
    PodcastTTS --> AudioStore

    User -->|Request Video| VideoAPI["/api/generate/video"]:::process
    VideoAPI --> VideoGen["generate_scene_video() (src/video.py)"]:::process
    VideoGen --> LTXModel["LTX-2 19B / CogVideoX Engine"]:::ai
    LTXModel --> VideoStore["/assets/videos/"]:::storage

    %% --- Presentation Layer ---
    ImageStore --> WebUI["Web Client (web/modes.html & web/assets/)"]:::frontend
    AudioStore --> WebUI
    VideoStore --> WebUI
    ExtractedData --> WebUI

    User <-->|Story / Study Mode UI| WebUI
    User -->|Export All| ZipService["Package ZIP (src/library.py)"]:::process
    ZipService --> Download[("Downloadable .zip Package")]:::storage
```

---

## 🛠️ Tech Stack

| Layer | Technology & Libraries | Description |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10+, FastAPI, Uvicorn | High-performance asynchronous REST API server |
| **AI Intelligence / LLMs** | Google Gemini (1.5 Flash/Pro), DeepSeek | Document reading, entity & scene extraction, podcast scripting, Q&A |
| **NLP & Vision** | Spacy (`en_core_web_sm`), Tesseract OCR | Named Entity Recognition (NER), layout OCR for scanned PDFs |
| **Speech Synthesis (TTS)** | ElevenLabs, Deepgram, Edge-TTS, Pollinations TTS | Multi-speaker TTS, voice cloning, automatic text chunking |
| **Visual & Video AI** | DeAPI (Flux), Pollinations AI, LTX-2 19B, CogVideoX | Character portrait art, scene galleries, video synthesis |
| **Database & Storage** | SQLModel, SQLite, Supabase | Book metadata, cached SSML scripts, user libraries, media asset paths |
| **Document Parsing** | PyPDF2, EbookLib, BeautifulSoup4 | Native PDF, EPUB, and TXT parsing engines |
| **Frontend UI** | HTML5, Vanilla CSS3 (Glassmorphism), JavaScript (ES6+) | Responsive dashboard, modal audio/video players, storybook reader |

---

## 📋 Prerequisites & Installation

### 1. System Requirements

- **Python 3.10 or higher**
- **Git**
- **Tesseract OCR** (Required for scanned PDF document parsing):
  - **Windows**: Download installer from [UB Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH.
  - **macOS**: `brew install tesseract`
  - **Linux**: `sudo apt-get install tesseract-ocr`

---

### 2. Step-by-Step Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/spigelspike/Book2Vision.git
   cd Book2Vision
   ```

2. **Create and Activate Virtual Environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download Spacy Language Model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the project root directory (see `.env.example`). Below is the configuration key reference:

```env
# ==========================================
# Primary LLM API Keys
# ==========================================
# Supports comma-separated keys for load balancing & key rotation
GEMINI_API_KEY=your_gemini_api_key_1,your_gemini_api_key_2
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# ==========================================
# Audio Synthesis (TTS) Keys
# ==========================================
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
PODCAST_API_KEY=your_podcast_dedicated_api_key

# ==========================================
# Visual Generation Keys
# ==========================================
DEAPI_API_KEY=your_deapi_api_key
POLLINATIONS_API_KEY=your_pollinations_api_key

# ==========================================
# Storage & Database (Optional Supabase Sync)
# ==========================================
DATABASE_URL=sqlite:///./book2vision.db
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

---

## 🚀 Running the Application

1. **Start the Server**:
   ```bash
   python src/server.py
   ```
   *Or directly with Uvicorn:*
   ```bash
   uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Open Web Portal**:
   Navigate to `http://localhost:8000` in your web browser.

3. **Transform a Book**:
   - Upload a PDF, EPUB, or TXT file.
   - Choose between **Story Mode** or **Study Mode**.
   - Trigger visual galleries, audiobooks, podcasts, or Q&A chatbot features.

---

## 📡 API Reference Matrix

The FastAPI backend exposes modular endpoints defined across `src/routers/`:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/upload` | `POST` | Uploads book, extracts text, runs semantic analysis & background cover generation |
| `/api/generate/analysis` | `POST` | Manually triggers Gemini LLM semantic analysis on book digest |
| `/api/generate/audio` | `POST` | Synthesizes TTS audiobook audio using selected provider (ElevenLabs/Deepgram/Edge-TTS) |
| `/api/generate/visuals` | `POST` | Generates cover poster, character portraits, and scene art |
| `/api/generate/video` | `POST` | Generates animated scene video highlights via LTX-2 / CogVideoX |
| `/api/content/podcast` | `POST` | Generates multi-speaker conversational AI podcast script & audio |
| `/api/content/storybook` | `GET` | Returns page-by-page illustrated storybook dataset |
| `/api/content/qa` | `POST` | Queries context-backed AI chatbot about book contents |
| `/api/library` | `GET` | Fetches saved books from database with metadata and thumbnails |
| `/api/library/{book_id}/export` | `GET` | Packages book text, analysis, audio, and images into downloadable `.zip` |

---

## 📂 Project Directory Structure

```text
book2vision/
├── src/
│   ├── server.py             # FastAPI app entry point, CORS, & static mounts
│   ├── config.py             # Environment config, key allocation, & defaults
│   ├── state.py              # Central application state manager
│   ├── database.py           # SQLModel database schema & engine
│   ├── ingestion.py          # PDF/EPUB/TXT extraction & Tesseract/Gemini OCR
│   ├── text_sampler.py       # Smart book digestion & text chunking
│   ├── analysis.py           # Gemini LLM narrative extraction & entity mapping
│   ├── audio.py              # Multi-provider TTS engine, SSML, & chunking
│   ├── visuals.py            # DeAPI (Flux) & Pollinations image generators
│   ├── video.py              # LTX-2 & CogVideoX video summary synthesis
│   ├── podcast.py            # Script generator & multi-speaker audio builder
│   ├── storybook.py          # Page-by-page illustrated storybook generator
│   ├── knowledge.py          # Intelligent Q&A chatbot & quiz engine
│   ├── library.py            # Persistent library manager & ZIP exporter
│   └── routers/              # Modular FastAPI API routers
│       ├── upload.py         # Ingestion endpoints
│       ├── generation.py     # Audio, visual, and video generation routes
│       ├── content.py        # Podcast, storybook, and Q&A routes
│       ├── library.py        # Library CRUD & export routes
│       └── music.py          # Background music routes
├── web/                      # Frontend web application
│   ├── assets/               # CSS styling, JS modules, and project media
│   │   ├── hero.png          # README & Hero Banner graphic
│   │   ├── dual_mode.png     # README Story Mode vs Study Mode graphic
│   │   └── styles/           # UI CSS stylesheets
│   └── modes.html            # Main web portal interface
├── tests/                    # Unit & integration test suite
├── .env.example              # Environment variables template
├── Dockerfile                # Container deployment file
├── pipeline.md               # Visual system pipeline documentation
├── requirements.txt          # Python dependencies manifest
└── README.md                 # System documentation
```

---

## 💡 Troubleshooting & FAQ

<details>
<summary><b>1. TesseractNotFoundError: tesseract is not installed or it's not in your PATH</b></summary>
<br />
Ensure Tesseract OCR is installed on your OS. On Windows, verify `C:\Program Files\Tesseract-OCR` is added to your environment variables PATH.
</details>

<details>
<summary><b>2. Spacy Model Missing: OSError: [E050] Can't find model 'en_core_web_sm'</b></summary>
<br />
Run `python -m spacy download en_core_web_sm` inside your activated virtual environment.
</details>

<details>
<summary><b>3. Deepgram API 400 Error: Character Limit Exceeded</b></summary>
<br />
Deepgram has a 2,000 character limit per request. Book2Vision handles this automatically by chunking text into sub-sentences in `src/audio.py`. Ensure your API key has active credits.
</details>

<details>
<summary><b>4. DeAPI 401 Unauthorized / Image Generation Fallback</b></summary>
<br />
If your DeAPI key expires or fails, Book2Vision automatically falls back to **Pollinations AI** for continuous image generation.
</details>

---

## 📄 License

This project is open-source and intended for educational, research, and personal use.

---

<p align="center">
  Crafted with ❤️ by the <b>Book2Vision</b> Team
</p>
