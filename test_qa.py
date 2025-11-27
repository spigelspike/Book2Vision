import requests
import json

url = "http://localhost:8000/api/qa"
data = {"question": "What is the main theme of the story?"}

try:
    print("Testing Q&A Endpoint...")
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
