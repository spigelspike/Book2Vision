import requests
import json

base_url = "http://localhost:8000/api/entity_image"
entities = ["Meenakshi", "Yakshi"]

for name in entities:
    print(f"Testing entity image for: {name}")
    try:
        response = requests.get(f"{base_url}/{name}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
