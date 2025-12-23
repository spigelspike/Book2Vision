# Book2Vision

**Book2Vision** is an automated system designed to transform digital books (PDF, EPUB, TXT) into complete multimedia packages, including audiobooks, video summaries, image packs, and knowledge tools.

## Features

*   **Ingestion**: Supports PDF, EPUB, and TXT formats.
*   **Analysis**: Extracts text, identifies chapters, and performs semantic analysis.
*   **Audiobook**: Generates audiobooks using TTS.
3.  Install Tesseract OCR (required for scanned PDFs).
4.  Download Spacy model:
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Configuration

1.  Clone the repository.
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Install Spacy model:
    ```bash
    python -m spacy download en_core_web_sm
    ```
5.  Create a `.env` file in the root directory and add your API keys (see `.env.example`):
    ```env
    GEMINI_API_KEY=your_key_here
    ELEVENLABS_API_KEY=your_key_here
    # Add other keys as needed
    ```

## How to Run

1.  Start the server:
    ```bash
    python src/server.py
    ```
   
2.  Open your browser and navigate to `http://localhost:8000`.
3.  Upload a book to start the transformation.
