import requests

def test_pollinations_tts():
    # Trying different models or just default
    url = "https://text.pollinations.ai/hello%20world?model=tts"
    url2 = "https://text.pollinations.ai/hello%20world?model=tts-1"
    url3 = "https://gen.pollinations.ai/audio/hello%20world?voice=nova"
    url4 = "https://gen.pollinations.ai/openai-audio/hello%20world?voice=nova"

    for u in [url, url2, url3, url4]:
        print(f"Fetching {u}")
        try:
            response = requests.get(u)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            if response.status_code == 200:
                print(f"Success! Content-Type: {response.headers.get('content-type')}, len: {len(response.content)}")
                if "audio" in response.headers.get('content-type', ''):
                    print("Found audio endpoint!")
                    break
            else:
                print(response.text[:200])
        except Exception as e:
            print(e)
        print("-" * 40)

if __name__ == "__main__":
    test_pollinations_tts()
