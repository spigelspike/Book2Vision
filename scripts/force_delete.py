from src.library import LibraryManager
import os

def force_delete():
    # Initialize manager
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_upload")
    manager = LibraryManager(upload_dir)
    
    ids_to_delete = [7, 8]
    
    for book_id in ids_to_delete:
        print(f"Attempting to delete book ID: {book_id}")
        success = manager.delete_book(book_id)
        if success:
            print(f"✅ Successfully deleted book {book_id}")
        else:
            print(f"❌ Failed to delete book {book_id} (Not found?)")

if __name__ == "__main__":
    force_delete()
