import os

def cleanup_file(filepath):
    print(f"Cleaning {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Remove residual mojibake for VS16 (ï¸)
        # It appears as 'ï¸' in the text if it was double-encoded
        replacements = {
            "🎙️ï¸ ": "🎙️",
            "🖼️ï¸ ": "🖼️",
            "ï¸ ": "", # Just remove it if it's standing alone or attached wrongly
        }
        
        new_text = text
        count = 0
        for bad, good in replacements.items():
            if bad in new_text:
                count += new_text.count(bad)
                new_text = new_text.replace(bad, good)
        
        if count > 0:
            print(f"Cleaned {count} residuals in {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)
        else:
            print(f"No residuals found in {filepath}")
            
    except Exception as e:
        print(f"Error cleaning {filepath}: {e}")

if __name__ == "__main__":
    cleanup_file("web/index.html")
