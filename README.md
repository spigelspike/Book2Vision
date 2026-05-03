# Book2Vision

**Book2Vision** is an automated system that transforms digital books (PDF, EPUB, TXT) into complete multimedia packages — audiobooks, visual scene galleries, character portraits, AI podcasts, interactive storybooks, video summaries, and intelligent Q&A.

## Features

- **Multi-Format Ingestion** — Supports PDF (including scanned via OCR), EPUB, and TXT formats
- **Semantic Analysis** — Extracts characters, scenes, themes, and relationships using Gemini AI
- **Audiobook Generation** — Full TTS audiobooks with multiple provider support (ElevenLabs, Deepgram, Edge TTS)
- **Visual Scene Gallery** — AI-generated illustrations for key scenes with carousel viewer
- **Character Portraits** — Consistent character art with reference sheets and multiple art styles
- **AI Podcast** — Multi-voice conversational podcasts discussing the book
- **Interactive Storybook** — Illustrated page-by-page storybook adaptation
- **Video Generation** — Animated scene videos from generated illustrations
- **Q&A Chatbot** — Ask questions about the book with AI-powered answers
- **Book Library** — Persistent library with cover art, metadata, and reload support
- **Download Bundle** — Export all generated content as a ZIP package

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| AI/NLP | Google Gemini, DeepSeek, Spacy |
| Audio | ElevenLabs, Deepgram, Edge TTS |
| Image Gen | Pollinations AI, DeAPI |
| Document Processing | PyPDF2, EbookLib, Tesseract OCR |
| Frontend | Vanilla HTML/CSS/JS (Glassmorphism UI) |
| Database | SQLModel (SQLite) |

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/book2vision.git
   cd book2vision
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Tesseract OCR (required for scanned PDFs):
   - **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

5. Download the Spacy language model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

6. Create a `.env` file in the root directory (see `.env.example`):
   ```env
   GEMINI_API_KEY=your_key_here
   ELEVENLABS_API_KEY=your_key_here
   DEEPSEEK_API_KEY=your_key_here
   DEAPI_API_KEY=your_key_here
   DEEPGRAM_API_KEY=your_key_here
   ```

## How to Run

1. Start the server:
   ```bash
   python src/server.py
   ```

2. Open your browser and navigate to `http://localhost:8000`

3. Upload a book to start the transformation.

## Project Structure

```
book2vision/
├── src/
│   ├── server.py          # FastAPI app + route setup
│   ├── routers/           # API route modules
│   │   ├── upload.py      # Book upload & ingestion
│   │   ├── generation.py  # Audio, visuals, portraits
│   │   ├── content.py     # Story, Q&A, podcast, storybook
│   │   └── library.py     # Library CRUD operations
│   ├── models.py          # Pydantic request models
│   ├── state.py           # App state & shared config
│   ├── ingestion.py       # Document parsing
│   ├── analysis.py        # Semantic analysis
│   ├── audio.py           # TTS audio generation
│   ├── visuals.py         # Image generation
│   ├── knowledge.py       # Q&A and quizzes
│   ├── podcast.py         # Podcast generation
│   ├── storybook.py       # Storybook generation
│   ├── video.py           # Video generation
│   ├── library.py         # Library manager
│   └── config.py          # Environment config
├── web/                   # Frontend (HTML/CSS/JS)
├── tests/                 # Test suite
├── scripts/               # Dev utilities & debug scripts
└── requirements.txt
```

## License

This project is for educational and personal use.
