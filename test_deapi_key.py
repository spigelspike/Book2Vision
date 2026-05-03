import requests

API_KEY = "8504|SEyKrvlrdLAOLHrD4lrGsKO4r8ht4qiVRqGWMb03f760c85f"

url = "https://api.deapi.ai/api/v1/client/txt2img"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
payload = {
    "prompt": "cat",
    "model": "Flux1schnell",
    "width": 512,
    "height": 512,
    "steps": 4
}
response = requests.post(url, headers=headers, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

url_balance = "https://api.deapi.ai/api/v2/account/balance"
response_balance = requests.get(url_balance, headers=headers)
print(f"Balance Status: {response_balance.status_code}")
print(f"Balance Response: {response_balance.text}")
