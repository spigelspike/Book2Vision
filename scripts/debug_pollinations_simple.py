import requests
import time
import urllib.parse

def test_pollinations_simple():
    print("Testing Pollinations with requests...")
    prompt = "A beautiful sunset"
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed=42&width=1024&height=1024&model=flux&nologo=true&enhance=true"
    
    print(f"URL: {url}")
    
    start = time.time()
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Success! Time: {time.time() - start:.2f}s")
            with open("debug_pollinations.jpg", "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pollinations_simple()
