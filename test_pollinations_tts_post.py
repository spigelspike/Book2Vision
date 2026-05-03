import requests

def test_pollinations_tts():
    # Trying the POST endpoint
    url = "https://gen.pollinations.ai/v1/audio/speech"
    print(f"Fetching {url}")
    try:
        response = requests.post(url, json={
            "model": "elevenlabs",
            "input": "Hello world from Pollinations",
            "voice": "nova"
        })
        print(f"Status: {response.status_code}")
        print(response.text[:200])
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_pollinations_tts()
