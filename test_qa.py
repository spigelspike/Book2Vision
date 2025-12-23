import requests
import os

BASE_URL = "http://localhost:8000"

def test_qa():
    print("=== Testing Ask Book AI ===")
    
    # 1. Create a dummy text file
    filename = "test_book.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("The quick brown fox jumps over the lazy dog. The fox was named Felix. The dog was named Rex. They lived in a small village called Greenvalley.")
        
    # 2. Upload
    print("Uploading book...")
    with open(filename, "rb") as f:
        files = {"file": f}
        try:
            res = requests.post(f"{BASE_URL}/api/upload", files=files)
            if res.status_code == 200:
                print("✅ Upload successful")
            else:
                print(f"❌ Upload failed: {res.text}")
                return
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

    # 3. Ask Question
    print("Asking question...")
    question = "What was the fox's name?"
    try:
        res = requests.post(f"{BASE_URL}/api/qa", json={"question": question})
        if res.status_code == 200:
            answer = res.json().get("answer")
            print(f"✅ QA Success. Answer: {answer}")
        else:
            print(f"❌ QA Failed: {res.text}")
    except Exception as e:
        print(f"❌ QA Connection failed: {e}")
        
    # Cleanup
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_qa()
