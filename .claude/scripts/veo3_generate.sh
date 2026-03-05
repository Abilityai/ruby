#!/bin/bash

# Veo 3 Video Generation Script
# Generates an 8-second video from a text prompt using Google Vertex AI
#
# Usage: ./veo3_generate.sh "Your prompt here" [output_file.mp4]
# Example: ./veo3_generate.sh "A mountain lake at sunrise" ~/Downloads/lake.mp4
#
# Requires: gcloud CLI authenticated (run: gcloud auth login)

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../.env" 2>/dev/null || true

# Defaults from .env or fallback
PROJECT_ID="${VEO3_PROJECT_ID:-mcp-server-project-455215}"
LOCATION="${VEO3_LOCATION:-us-central1}"
MODEL="${VEO3_MODEL:-veo-3.0-generate-001}"

# Check args
if [ -z "$1" ]; then
    echo "Usage: $0 \"<prompt>\" [output_file.mp4] [aspect_ratio]"
    echo "Example: $0 \"A serene mountain lake at sunrise\" ~/Downloads/video.mp4 16:9"
    echo "Aspect ratios: 16:9 (horizontal), 9:16 (vertical)"
    exit 1
fi

PROMPT="$1"
OUTPUT_FILE="${2:-$HOME/Downloads/veo3_$(date +%Y%m%d_%H%M%S).mp4}"
ASPECT_RATIO="${3:-16:9}"

echo "=== Veo 3 Video Generation ==="
echo "Prompt: $PROMPT"
echo "Output: $OUTPUT_FILE"
echo "Aspect Ratio: $ASPECT_RATIO"
echo ""

# Get OAuth token
echo "Getting auth token..."
ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)
if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token. Run: gcloud auth login"
    exit 1
fi

# API endpoint
API_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:predictLongRunning"

# Generate video (start operation)
echo "Starting video generation..."
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"instances\": [{\"prompt\": \"$PROMPT\"}],
    \"parameters\": {
      \"aspectRatio\": \"$ASPECT_RATIO\",
      \"sampleCount\": 1,
      \"durationSeconds\": 8,
      \"resolution\": \"720p\"
    }
  }")

# Extract operation name
OPERATION_NAME=$(echo "$RESPONSE" | jq -r '.name // empty')

if [ -z "$OPERATION_NAME" ]; then
    echo "Error: Failed to start generation"
    echo "$RESPONSE" | jq .
    exit 1
fi

echo "Operation started: $OPERATION_NAME"
echo ""

# Poll for completion
FETCH_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:fetchPredictOperation"

echo "Waiting for video generation (typically 2-5 minutes)..."
while true; do
    sleep 30
    echo -n "."

    RESULT=$(curl -s -X POST "$FETCH_URL" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"operationName\": \"$OPERATION_NAME\"}")

    DONE=$(echo "$RESULT" | jq -r '.done // false')

    if [ "$DONE" == "true" ]; then
        echo ""
        echo "Generation complete!"

        # Check for video
        VIDEO_DATA=$(echo "$RESULT" | jq -r '.response.videos[0].bytesBase64Encoded // empty')

        if [ -n "$VIDEO_DATA" ]; then
            echo "$VIDEO_DATA" | base64 -d > "$OUTPUT_FILE"
            echo "Video saved to: $OUTPUT_FILE"
            echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
        else
            echo "Error: No video in response"
            echo "$RESULT" | jq .
            exit 1
        fi
        break
    fi
done

echo ""
echo "Done!"
