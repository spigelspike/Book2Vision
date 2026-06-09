import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_pollinations_tts():
    # Trying the POST endpoint
    url = "https://gen.pollinations.ai/v1/audio/speech"
    key = os.getenv("POLLINATIONS_API_KEY")
    print(f"Fetching {url}")
    try:
        response = requests.post(url, 
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "openai-audio",
                "input": "Hello world from Pollinations using openai-audio model",
                "voice": "nova"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Success! Length: {len(response.content)}")
            with open("test_pollinations.mp3", "wb") as f:
                f.write(response.content)
        else:
            print(response.text[:200])
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_pollinations_tts()

