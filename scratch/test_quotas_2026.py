import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

# Based on the list I just saw
models_to_test = [
    "gemini-2.0-flash",
    "gemini-2.5-flash-native-audio-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
]

for model in models_to_test:
    # Use full path if it has 'models/'
    m_name = model if model.startswith("models/") else f"models/{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "say hi"}]}]}
    response = requests.post(url, json=payload)
    print(f"Model {model}: Status {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text[:100]}")
    else:
        print(f"  Success!")
        break
