"""Quick test script to verify deAPI v2 endpoints work with your API key."""
import requests

API_KEY = "8504|SEyKrvlrdLAOLHrD4lrGsKO4r8ht4qiVRqGWMb03f760c85f"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Test 1: Check balance (simplest v2 endpoint)
print("=== Test 1: Check Balance (v2) ===")
r = requests.get("https://api.deapi.ai/api/v2/account/balance", headers=headers)
print(f"Status: {r.status_code} | Response: {r.text}")

# Test 2: List available txt2img models
print("\n=== Test 2: List Models (v2) ===")
r = requests.get("https://api.deapi.ai/api/v2/models?filter[inference_types]=txt2img", headers=headers)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    models = data.get("data", [])
    print(f"Found {len(models)} txt2img models:")
    for m in models[:5]:
        print(f"  - {m.get('slug')} ({m.get('name')})")
else:
    print(f"Response: {r.text}")

# Test 3: Submit a tiny image generation job
print("\n=== Test 3: Generate Image (v2) ===")
payload = {
    "prompt": "A simple red cat sitting on a blue chair, digital art",
    "model": "Flux1schnell",
    "width": 512,
    "height": 512,
    "steps": 4,
    "guidance": 0,
    "seed": 42
}
r = requests.post("https://api.deapi.ai/api/v2/images/generations", headers=headers, json=payload)
print(f"Status: {r.status_code} | Response: {r.text}")
