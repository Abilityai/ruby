#!/bin/bash

# Veo 3 Image-to-Video Generation Script
# Generates an 8-second video from an image + optional prompt
#
# Usage: ./veo3_generate_from_image.sh <image_file.png> "Optional prompt" [output_file.mp4]
# Example: ./veo3_generate_from_image.sh dashboard.png "Animate with breathing effects" ~/Downloads/video.mp4
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
    echo "Usage: $0 <image_file> [\"prompt\"] [output_file.mp4] [aspect_ratio]"
    echo "Example: $0 dashboard.png \"Animate with pulsing effects\" ~/Downloads/video.mp4 16:9"
    echo "Aspect ratios: 16:9 (horizontal), 9:16 (vertical)"
    exit 1
fi

IMAGE_FILE="$1"
PROMPT="${2:-}"
OUTPUT_FILE="${3:-$HOME/Downloads/veo3_$(date +%Y%m%d_%H%M%S).mp4}"
ASPECT_RATIO="${4:-16:9}"

# Check if image file exists
if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: Image file not found: $IMAGE_FILE"
    exit 1
fi

echo "=== Veo 3 Image-to-Video Generation ==="
echo "Image: $IMAGE_FILE"
echo "Prompt: ${PROMPT:-[none]}"
echo "Output: $OUTPUT_FILE"
echo "Aspect Ratio: $ASPECT_RATIO"
echo ""

# Detect MIME type
echo "Detecting image type..."
MIME_TYPE=""
FILE_LOWER=$(echo "$IMAGE_FILE" | tr '[:upper:]' '[:lower:]')
case "$FILE_LOWER" in
    *.png) MIME_TYPE="image/png" ;;
    *.jpg|*.jpeg) MIME_TYPE="image/jpeg" ;;
    *.webp) MIME_TYPE="image/webp" ;;
    *)
        echo "Error: Unsupported image format. Use PNG, JPEG, or WebP"
        exit 1
        ;;
esac

# Encode image to base64
echo "Encoding image..."
IMAGE_BASE64=$(base64 -i "$IMAGE_FILE" | tr -d '\n')

# Get OAuth token
echo "Getting auth token..."
ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)
if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token. Run: gcloud auth login"
    exit 1
fi

# API endpoint
API_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:predictLongRunning"

# Build JSON payload in temp file
TEMP_JSON=$(mktemp)
trap "rm -f $TEMP_JSON" EXIT

if [ -n "$PROMPT" ]; then
    # With prompt
    cat > "$TEMP_JSON" <<EOF
{
    "instances": [{
        "prompt": "$PROMPT",
        "image": {
            "bytesBase64Encoded": "$IMAGE_BASE64",
            "mimeType": "$MIME_TYPE"
        }
    }],
    "parameters": {
        "aspectRatio": "$ASPECT_RATIO",
        "sampleCount": 1,
        "durationSeconds": 8,
        "resolution": "720p"
    }
}
EOF
else
    # Image only (no prompt)
    cat > "$TEMP_JSON" <<EOF
{
    "instances": [{
        "image": {
            "bytesBase64Encoded": "$IMAGE_BASE64",
            "mimeType": "$MIME_TYPE"
        }
    }],
    "parameters": {
        "aspectRatio": "$ASPECT_RATIO",
        "sampleCount": 1,
        "durationSeconds": 8,
        "resolution": "720p"
    }
}
EOF
fi

# Generate video (start operation)
echo "Starting video generation..."
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$TEMP_JSON")

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
