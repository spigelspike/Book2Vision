import requests
from PIL import Image
from io import BytesIO

url = "http://localhost:8000/api/assets/entities/entity_Meenakshi.jpg"

print(f"Downloading image from {url}...")
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Size: {len(response.content)} bytes")
        
        # Verify it's a valid image
        try:
            img = Image.open(BytesIO(response.content))
            print(f"Valid Image: Format={img.format}, Size={img.size}, Mode={img.mode}")
        except Exception as e:
            print(f"❌ Invalid image data: {e}")
    else:
        print("❌ Failed to download image")
except Exception as e:
    print(f"Error: {e}")
