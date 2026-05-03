"""Library router — CRUD operations for the book library."""

import os
import traceback
from fastapi import APIRouter, HTTPException

from src.state import state, UPLOAD_DIR, library_manager
from src.ingestion import ingest_book
from src.analysis import semantic_analysis

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/library")
async def get_library():
    """Get all books in the library."""
    try:
        return {"books": library_manager.get_books()}
    except Exception as e:
        print(f"❌ Library fetch error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch library")


@router.delete("/library/{book_id}")
async def delete_book(book_id: int):
    """Delete a book from the library."""
    success = library_manager.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}


@router.post("/library/load/{book_id}")
async def load_book(book_id: int):
    """Load a book from the library into active state."""
    state.book_id = book_id
    book = library_manager.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    filename = book["filename"]
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        # Clean up if file is missing
        library_manager.delete_book(book_id)
        raise HTTPException(status_code=404, detail="Book file not found on server")
    
    try:
        # Try to load from DB first
        full_text = library_manager.get_book_full_text(book_id)
        analysis = library_manager.get_analysis(book_id)
        
        if full_text and analysis:
            print(f"✅ Loaded book from DB: {book['title']}")
            state.full_text = full_text
            state.analysis_result = analysis
            state.ingestion_result = {
                "title": book["title"],
                "author": book["author"],
                "body": full_text,
                "full_text": full_text,
                "filename": filename
            }
        else:
            print(f"⚠️ DB miss. Re-ingesting book: {book['title']}...")
            # Re-ingest (fast, mostly reading text)
            ingestion_result = await ingest_book(file_path)
            ingestion_result["filename"] = filename
            
            # Update state
            state.ingestion_result = ingestion_result
            state.full_text = ingestion_result.get("full_text", "")
            
            # Re-analyze
            print(f"Re-analyzing book: {book['title']}...")
            analysis = await semantic_analysis(state.full_text)
            state.analysis_result = analysis
            
            # Save back to DB for next time
            library_manager.add_book(book, full_text=state.full_text)
            library_manager.save_analysis(book_id, analysis)
        
        return {
            "message": "Book loaded successfully",
            "filename": filename,
            "analysis": state.analysis_result,
            "title": book["title"],
            "author": book["author"]
        }
    except Exception as e:
        print(f"Error loading book: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load book: {str(e)}")
