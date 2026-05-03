import os

file_path = r'c:\Users\share\Desktop\PROJECT\book2visionn\web\style.css'

try:
    with open(file_path, 'rb') as f:
        content = f.read()

    print(f"Read {len(content)} bytes.")
    
    # Check for null bytes
    null_count = content.count(b'\x00')
    print(f"Found {null_count} null bytes.")

    if null_count > 0:
        # Remove null bytes
        clean_content = content.replace(b'\x00', b'')
        
        # Try to decode to ensure it's valid text
        text = clean_content.decode('utf-8')
        
        # Write back as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print("Successfully cleaned and saved style.css")
    else:
        print("No null bytes found. File might be okay or corrupted differently.")

except Exception as e:
    print(f"Error: {e}")
