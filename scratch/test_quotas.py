import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

models_to_test = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-pro",
    "gemini-1.0-pro"
]

for model in models_to_test:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "say hi"}]}]}
    response = requests.post(url, json=payload)
    print(f"Model {model}: Status {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text[:100]}")
