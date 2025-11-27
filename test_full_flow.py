import requests

url = "http://localhost:8000/api/upload"
files = {'file': open('test_book.txt', 'rb')}

print("Uploading book...")
response = requests.post(url, files=files)
print(f"Upload Status: {response.status_code}")
print(f"Upload Response: {response.json()}")

if response.status_code == 200:
    print("\nTesting Q&A...")
    qa_url = "http://localhost:8000/api/qa"
    qa_data = {"question": "What did Alex find in the cave?"}
    qa_response = requests.post(qa_url, json=qa_data)
    print(f"Q&A Status: {qa_response.status_code}")
    print(f"Q&A Answer: {qa_response.json()}")
