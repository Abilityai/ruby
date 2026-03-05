#!/usr/bin/env python3
"""Poll Veo 3 operation status and download result"""

import subprocess
import requests
import json
import base64
import sys
import time

# Operation name from the generate call
operation_name = sys.argv[1] if len(sys.argv) > 1 else "projects/mcp-server-project-455215/locations/us-central1/publishers/google/models/veo-3.0-generate-001/operations/92199a2a-6b1d-4299-b110-737d3605ef80"

# Get access token from gcloud
result = subprocess.run(['gcloud', 'auth', 'print-access-token'], capture_output=True, text=True)
access_token = result.stdout.strip()

if not access_token:
    print("Failed to get access token")
    exit(1)

# Extract components
parts = operation_name.split('/')
project_id = parts[1]
location = parts[3]
model = parts[7]

url = f"https://{location}-aiplatform.googleapis.com/v1/{operation_name}"

# Alternative: use fetchPredictOperation endpoint
fetch_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:fetchPredictOperation"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

print(f"Polling operation: {operation_name}")
print(f"URL: {fetch_url}")

response = requests.post(fetch_url, headers=headers, json={"operationName": operation_name})

print(f"\nStatus: {response.status_code}")
data = response.json()

if 'done' in data and data['done']:
    print("Video generation COMPLETE!")

    if 'response' in data and 'videos' in data['response']:
        videos = data['response']['videos']
        print(f"Generated {len(videos)} video(s)")

        for i, video in enumerate(videos):
            if 'bytesBase64Encoded' in video:
                video_bytes = base64.b64decode(video['bytesBase64Encoded'])
                filename = f"
                with open(filename, 'wb') as f:
                    f.write(video_bytes)
                print(f"Saved video to: {filename}")
    else:
        print("No videos in response")
        print(json.dumps(data, indent=2))
else:
    print("Still processing...")
    print(json.dumps(data, indent=2))
