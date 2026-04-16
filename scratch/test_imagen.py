import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

# Testing Imagen 4.0 or 3.0 via Generative Language API
model = "models/imagen-4.0-generate-001" # Or try imagen-3.0-generate-001
url = f"https://generativelanguage.googleapis.com/v1beta/{model}:predict?key={api_key}"

prompt = "A luxury wedding invitation card for John and Jane, elegant gold script text, floral white background, professional photography"

payload = {
    "instances": [
        {
            "prompt": prompt
        }
    ],
    "parameters": {
        "sampleCount": 1
    }
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
try:
    print(f"Response: {response.text[:500]}")
except:
    pass
