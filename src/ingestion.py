import os
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import asyncio
from google import genai
from src.config import GEMINI_API_KEY
import time
import json
from functools import partial

async def ingest_book(file_path):
    """
    Detects file type and extracts text (Async).
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return await extract_text_from_pdf(file_path)
    elif ext == '.txt':
        return await extract_text_from_txt(file_path)
    elif ext == '.epub':
        return await extract_text_from_epub(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

async def extract_text_from_pdf(file_path):
    text = ""
    try:
        # Run CPU-bound PDF parsing in a separate thread
        def parse_pdf():
            local_text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        local_text += extracted + "\n"
            return local_text

        text = await asyncio.to_thread(parse_pdf)
            
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
    
    # Fallback to Gemini if text is empty or very short (likely scanned)
    if len(text.strip()) < 100:
        print("PDF seems scanned or empty. Using Gemini 1.5 Flash to read it...")
        return await extract_text_with_gemini(file_path)
        
    # Return dict for consistency if local extraction worked
    title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").replace("-", " ").title()
    return {"title": title, "body": text, "full_text": text}

async def extract_text_with_gemini(file_path):
    """
    Uploads file to Gemini and extracts text (Async).
    """
    # Fetch dynamically to handle UI updates
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("⚠️ GEMINI_API_KEY not found. Skipping Gemini extraction.")
        return {"title": "Error", "body": "GEMINI_API_KEY not found.", "full_text": "Error: GEMINI_API_KEY not found."}

    try:
        # Use helper to get best vision model
        from src.gemini_utils import get_gemini_model
        
        print(f"Uploading {file_path} to Gemini...")
        # Client creation is fast/local
        client, model_name = get_gemini_model("vision", api_key=api_key)
        
        # Upload file (Network I/O) -> Run in thread
        sample_file = await asyncio.to_thread(
            client.files.upload, path=file_path, config={"display_name": "Book Content"}
        )
        
        # Wait for processing (Non-blocking polling)
        while sample_file.state.name == "PROCESSING":
            print("Processing file...")
            await asyncio.sleep(2) # Non-blocking sleep
            # Check status (Network I/O) -> Run in thread
            sample_file = await asyncio.to_thread(
                client.files.get, name=sample_file.name
            )
            
        if sample_file.state.name == "FAILED":
            return {"title": "Error", "body": "Gemini failed to process file.", "full_text": "Error: Gemini processing failed."}
            
        print("File processed. Extracting structured content...")
        
        # 1. Try Structured JSON Extraction
        prompt_json = """
        You are a document understanding system performing layout-aware extraction
        on a scanned or digital book/story.

        Carefully analyze the pages and:

        1. Identify the **main title** of the story or book.
           - This is usually the largest, most prominent text near the beginning.
           - Do not use publisher names or series labels as the title.

        2. Identify the **author name** if it is clearly present.
           - If the author is not clearly indicated, return an empty string for author.

        3. Extract the **main narrative body text**:
           - The continuous story content.
           - Preserve reading order from top to bottom, left to right.
           - Preserve paragraphs and line breaks where they help readability.
           - Exclude:
             * page numbers
             * running headers and footers
             * table of contents
             * copyright pages
             * publisher info
             * chapter list pages without story content
             * illustration labels/captions unless they are clearly part of the story.

        Output Requirements (IMPORTANT):
        - Return a single, valid JSON object.
        - No markdown, no code fences, no comments.
        - Use exactly these keys:
          * "title"  : string
          * "author" : string
          * "body"   : string (the full readable story text)

        Example shape (do NOT include this as text, just follow the structure):
        {
          "title": "Example Title",
          "author": "Example Author",
          "body": "Full story text goes here..."
        }
        """

        # Helper for robust generation with retries (Async wrapper)
        async def generate_with_retry(client, model_name, inputs, config=None, retries=3):
            from google.api_core import exceptions
            for attempt in range(retries):
                try:
                    # Run blocking generation in thread
                    return await asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=inputs,
                        config=config
                    )
                except exceptions.ResourceExhausted:
                    wait = (2 ** attempt) * 5 + 5 # 10s, 15s, 25s...
                    print(f"⚠️ Quota exceeded (429). Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                except Exception as e:
                    if "429" in str(e): # Fallback if exception type isn't caught
                        wait = (2 ** attempt) * 5 + 5
                        print(f"⚠️ Quota exceeded (429). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise e
            raise Exception("Max retries exceeded for Gemini API.")

        try:
            print(f"Using model: {model_name}")
            
            response = await generate_with_retry(
                client,
                model_name,
                [sample_file, prompt_json],
                config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            return {
                "title": data.get("title", "Unknown Title"), 
                "author": data.get("author", "Unknown Author"),
                "body": data.get("body", ""), 
                "full_text": f"Title: {data.get('title', '')}\nAuthor: {data.get('author', '')}\n\n{data.get('body', '')}"
            }
        except Exception as e:
            print(f"Structured extraction failed: {e}")
            # Fallthrough to text extraction

        # 2. Fallback: Simple Text Extraction (Non-JSON)
        print("Structured extraction failed. Falling back to raw text extraction...")
        prompt_text = """
        Extract all readable text from this document in correct reading order.

        Guidelines:
        - Include only meaningful content: narrative text, chapter titles, headings that belong to the story.
        - Try to ignore:
          * page numbers
          * running headers and footers
          * watermarks
          * repeated navigation elements (e.g., "Chapter 1" repeated at top of each page).
        - Preserve basic paragraph breaks where they help readability.
        - Do not add commentary or explanation; return only the extracted text.
        """

        try:
            # Reuse model or get new one
            # client, model_name already defined
            response = await generate_with_retry(client, model_name, [sample_file, prompt_text])
            
            text = response.text
            lines = text.split('\n')
            title = lines[0] if lines else "Unknown Title"
            body = "\n".join(lines[1:]) if len(lines) > 1 else text
            
            return {"title": title, "body": body, "full_text": text}
        except Exception as e:
            print(f"Raw text extraction failed: {e}")
            # Fallthrough to OCR.space

        # 3. Fallback: OCR.space (Free API)
        print("Gemini failed. Falling back to OCR.space (Free API)...")
        try:
            import requests
            
            # Use 'helloworld' key for demo, or user key if available
            ocr_api_key = "helloworld" 
            
            def call_ocr_space():
                with open(file_path, 'rb') as f:
                    return requests.post(
                        'https://api.ocr.space/parse/image',
                        files={file_path: f},
                        data={'apikey': ocr_api_key, 'language': 'eng', 'isOverlayRequired': False}
                    )
            
            response = await asyncio.to_thread(call_ocr_space)
            
            result = response.json()
            if result.get('IsErroredOnProcessing') == False:
                parsed_results = result.get('ParsedResults', [])
                text = ""
                for page in parsed_results:
                    text += page.get('ParsedText', "") + "\n"
                
                if text.strip():
                    lines = text.split('\n')
                    title = lines[0] if lines else "OCR Result"
                    body = "\n".join(lines[1:]) if len(lines) > 1 else text
                    return {"title": title, "body": body, "full_text": text}
            else:
                print(f"OCR.space Error: {result.get('ErrorMessage')}")

        except Exception as e:
            print(f"OCR.space failed: {e}")

        return {"title": "Error", "body": "All AI models failed.", "full_text": "Error: Extraction failed."}

    except Exception as e:
        return {"title": "Error", "body": f"Gemini Extraction Failed: {e}", "full_text": f"Error: {e}"}

async def extract_text_from_txt(file_path):
    def read_txt():
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").replace("-", " ").title()
            return {"title": title, "body": text, "full_text": text}
    return await asyncio.to_thread(read_txt)

async def extract_text_from_epub(file_path):
    def read_epub():
        try:
            book = epub.read_epub(file_path)
            text = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text.append(soup.get_text())
            full_text = "\n".join(text)
            title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").replace("-", " ").title()
            return {"title": title, "body": full_text, "full_text": full_text}
        except Exception as e:
            print(f"Error reading EPUB: {e}")
            return {"title": "Error", "body": "", "full_text": ""}
            
    return await asyncio.to_thread(read_epub)

def clean_format(raw_text):
    # Basic cleaning
    lines = raw_text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)
