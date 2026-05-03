import sys
import os
import traceback

# Add project root to sys.path
sys.path.append(os.path.abspath(os.getcwd()))

try:
    from src.library import LibraryManager
    from src.database import init_db
    
    print("✅ Imports successful")
    
    # Initialize DB
    print("Initializing DB...")
    init_db()
    print("✅ DB Initialized")
    
    # Initialize LibraryManager
    print("Initializing LibraryManager...")
    upload_dir = os.path.join(os.getcwd(), "temp_upload")
    os.makedirs(upload_dir, exist_ok=True)
    
    lib_mgr = LibraryManager(upload_dir)
    print("✅ LibraryManager Initialized")
    
    # Try to get books
    print("Fetching books...")
    books = lib_mgr.get_books()
    print(f"✅ Fetched {len(books)} books")
    print("Books:", books)
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
