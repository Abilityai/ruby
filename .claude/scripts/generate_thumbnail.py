#!/usr/bin/env python3
"""
Generate YouTube thumbnails using Gemini 2.5 Flash Image API.
Supports 16:9 aspect ratio for horizontal thumbnails.

Usage:
    python generate_thumbnail.py "prompt" output_path.png
    python generate_thumbnail.py "prompt"  # saves to /tmp/thumbnail.png
"""

import requests
import base64
import sys
import os
from pathlib import Path

# Load API key from .env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ.setdefault(key, value)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"

def generate_thumbnail(prompt: str, output_path: str, aspect_ratio: str = "16:9"):
    """Generate a thumbnail image with specified aspect ratio."""
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {
                "aspectRatio": aspect_ratio
            }
        }
    }

    response = requests.post(URL, json=payload)
    data = response.json()

    if "candidates" not in data:
        print(f"Error: {data.get('error', data)}")
        return False

    parts = data["candidates"][0]["content"]["parts"]
    for part in parts:
        if "inlineData" in part:
            img_data = part["inlineData"]["data"]
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            print(f"Saved: {output_path}")
            return True

    print("Error: No image in response")
    return False

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Professional YouTube thumbnail"
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/thumbnail.png"
    generate_thumbnail(prompt, output)
