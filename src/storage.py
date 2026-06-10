import os
import mimetypes
from src.config import supabase_client

def upload_file_to_supabase(bucket_name: str, local_path: str, remote_filename: str) -> str:
    """
    Uploads a local file to a Supabase Storage bucket and returns the public URL.
    """
    if not supabase_client:
        print("WARNING: Supabase client not configured. Skipping upload.")
        return ""
        
    try:
        # Determine content type
        content_type, _ = mimetypes.guess_type(local_path)
        if not content_type:
            content_type = "application/octet-stream"

        with open(local_path, 'rb') as f:
            file_bytes = f.read()

        # Upload to Supabase (upsert=true overwrites if exists)
        res = supabase_client.storage.from_(bucket_name).upload(
            file=file_bytes,
            path=remote_filename,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        # Get public URL
        url = supabase_client.storage.from_(bucket_name).get_public_url(remote_filename)
        return url
    except Exception as e:
        print(f"ERROR: Supabase upload failed for {remote_filename}: {e}")
        # Return empty string on failure
        return ""

def delete_file_from_supabase(bucket_name: str, remote_filename: str) -> bool:
    """
    Deletes a file from a Supabase Storage bucket.
    """
    if not supabase_client:
        return False
        
    try:
        supabase_client.storage.from_(bucket_name).remove([remote_filename])
        return True
    except Exception as e:
        print(f"ERROR: Failed to delete {remote_filename} from {bucket_name}: {e}")
        return False

def get_public_url(bucket_name: str, remote_filename: str) -> str:
    """
    Returns the deterministic public URL for a file in a Supabase bucket.
    """
    if not supabase_client:
        return ""
    return supabase_client.storage.from_(bucket_name).get_public_url(remote_filename)
