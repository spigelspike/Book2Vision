# Book2Vision — Project Overview

**Book2Vision** is a state-of-the-art AI platform designed to bridge the gap between static literature and immersive multimedia experiences. It transforms traditional books into a rich ecosystem of cinematic visuals, emotive audio, interactive dialogues, and dynamic video summaries.

---

## 🌟 Project Vision
The core mission of Book2Vision is to redefine how we consume stories and information. By leveraging the latest breakthroughs in Generative AI, the platform turns reading from a solitary, text-based activity into a multi-sensory journey, making it more accessible, engaging, and memorable for modern audiences.

---

## 🚀 Key Features

### 1. Multi-Mode Interaction
- **Story Mode**: A cinematic experience with AI narration, character portraits, and scene-by-scene visual galleries.
- **Study Mode**: Deep academic analysis, intelligent Q&A, and interactive knowledge extraction for textbooks and non-fiction.

### 2. Intelligent Ingestion
- **Robust Parsing**: Supports PDF (including OCR for scans), EPUB, and TXT.
- **Semantic Analysis**: Automatically extracts characters, key scenes, settings, and narrative arcs using Gemini AI.

### 3. Multimedia Generation
- **Audiobooks & Podcasts**: Emotive TTS using ElevenLabs and Deepgram, plus conversational AI-hosted podcasts.
- **Visual Arts**: Dynamic image generation for scenes and characters with support for multiple art styles (Storybook, Anime, Cinematic, etc.).
- **Video Summaries**: High-fidelity video overviews generated using LTX-2 19B and CogVideoX models.

### 4. Interactive Engagement
- **Q&A Bot**: Context-aware chat system to discuss plot points, character motivations, or academic concepts.
- **Storybook Viewer**: A page-by-page illustrated adaptation of the book.

---

## 🛠 Technology Stack

### Frontend (UI/UX)
- **Core**: Vanilla HTML5, JavaScript (ES6+), and CSS3.
- **Design System**: A custom "Glassmorphism" design system with vibrant gradients, blurred backdrops, and fluid micro-animations.
- **Assets**: High-quality 4K background videos for immersive navigation.

### Backend (Infrastructure)
- **Framework**: FastAPI (Python) for high-performance asynchronous API handling.
- **Server**: Uvicorn for ASGI server implementation.
- **Database**: SQLite with SQLModel for persistent library management and user data.
- **Document Processing**: Tesseract OCR, PyPDF2, and EbookLib for sophisticated text extraction.

### AI & Machine Learning Ecosystem
- **LLMs**: Google Gemini (Core Intelligence), DeepSeek (Podcast Scripting).
- **Computer Vision**: Spacy for Named Entity Recognition (NER).
- **Audio (TTS)**: ElevenLabs, Deepgram, Edge TTS, and Pollinations TTS.
- **Image/Video Gen**: Pollinations AI, DeAPI, LTX-2, and CogVideoX.

---

## 🔄 User Journey
1. **Landing Page**: Introduction to the platform's vision and features.
2. **Authentication**: Secure Login/Signup with a customized onboarding flow.
3. **Mode Selection**: Users choose between "Story Mode" (Narrative) or "Study Mode" (Analysis).
4. **Dashboard/Upload**: Ingesting the book and initiating the AI analysis pipeline.
5. **Consumption**: Viewing generated visuals, listening to the audiobook, or chatting with the book.
6. **Library**: Managing a persistent collection of processed books.

---

## 📂 Project Architecture
```text
book2vision/
├── src/
│   ├── server.py          # FastAPI application & routing
│   ├── routers/           # Domain-specific API endpoints
│   ├── models.py          # Data structures & Pydantic models
│   ├── analysis.py        # AI narrative/semantic extraction
│   ├── audio.py           # Multi-provider TTS integration
│   ├── visuals.py         # Image & video generation logic
│   └── state.py           # Configuration & environment management
├── web/                   # High-fidelity frontend assets
│   ├── assets/            # CSS & JS modules
│   ├── res/               # Background videos & icons
│   └── modes.html         # Central navigation hub
└── data/                  # Persistent storage (Uploads/DB)
```

---

## 🛠 Setup & Development
Refer to the [README.md](file:///c:/Users/share/Desktop/PROJECT/book2visionn/README.md) for detailed installation instructions and environment configuration.
