#!/usr/bin/env python3
"""Test Veo 3 API call using gcloud credentials"""

import subprocess
import requests
import json

# Get access token from gcloud
result = subprocess.run(['gcloud', 'auth', 'print-access-token'], capture_output=True, text=True)
access_token = result.stdout.strip()

if not access_token:
    print("Failed to get access token. Run: gcloud auth login")
    exit(1)

print(f"Got access token: {access_token[:20]}...")

# Veo 3 API endpoint
project_id = "mcp-server-project-455215"
location = "us-central1"
model = "veo-3.0-generate-001"

url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:predictLongRunning"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

payload = {
    "instances": [
        {"prompt": "A serene mountain lake at sunrise with mist rising from the water, cinematic quality"}
    ],
    "parameters": {
        "aspectRatio": "16:9",
        "sampleCount": 1,
        "durationSeconds": 8,
        "resolution": "720p"
    }
}

print(f"\nCalling Veo 3 API...")
print(f"URL: {url}")
print(f"Prompt: {payload['instances'][0]['prompt']}")

response = requests.post(url, headers=headers, json=payload)

print(f"\nStatus: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
