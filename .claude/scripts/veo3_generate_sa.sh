#!/bin/bash

# Veo 3 Video Generation Script (Service Account Version)
# Uses a service account JSON key instead of gcloud CLI
#
# Usage: ./veo3_generate_sa.sh "Your prompt here" [output_file.mp4] [aspect_ratio]
# 
# Requires:
#   - GOOGLE_SERVICE_ACCOUNT_KEY_PATH env var pointing to JSON key file
#   - OR GOOGLE_SERVICE_ACCOUNT_KEY env var with JSON content
#   - jq and curl installed

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../.env" 2>/dev/null || true

# Config
PROJECT_ID="${VEO3_PROJECT_ID:-mcp-server-project-455215}"
LOCATION="${VEO3_LOCATION:-us-central1}"
MODEL="${VEO3_MODEL:-veo-3.0-generate-001}"

# Check args
if [ -z "$1" ]; then
    echo "Usage: $0 \"<prompt>\" [output_file.mp4] [aspect_ratio]"
    echo "Example: $0 \"A serene mountain lake at sunrise\" ~/Downloads/video.mp4 16:9"
    exit 1
fi

PROMPT="$1"
OUTPUT_FILE="${2:-$HOME/Downloads/veo3_$(date +%Y%m%d_%H%M%S).mp4}"
ASPECT_RATIO="${3:-16:9}"

echo "=== Veo 3 Video Generation (Service Account) ==="
echo "Prompt: $PROMPT"
echo "Output: $OUTPUT_FILE"
echo "Aspect Ratio: $ASPECT_RATIO"
echo ""

# Function to get access token from service account
get_access_token() {
    local key_file=""
    
    # Check for key file path
    if [ -n "$GOOGLE_SERVICE_ACCOUNT_KEY_PATH" ] && [ -f "$GOOGLE_SERVICE_ACCOUNT_KEY_PATH" ]; then
        key_file="$GOOGLE_SERVICE_ACCOUNT_KEY_PATH"
    elif [ -n "$GOOGLE_SERVICE_ACCOUNT_KEY" ]; then
        # Write key content to temp file
        key_file=$(mktemp)
        echo "$GOOGLE_SERVICE_ACCOUNT_KEY" > "$key_file"
        trap "rm -f $key_file" EXIT
    else
        echo "Error: No service account key found."
        echo "Set GOOGLE_SERVICE_ACCOUNT_KEY_PATH or GOOGLE_SERVICE_ACCOUNT_KEY"
        exit 1
    fi
    
    # Extract values from service account JSON
    local client_email=$(jq -r '.client_email' "$key_file")
    local private_key=$(jq -r '.private_key' "$key_file")
    local token_uri=$(jq -r '.token_uri // "https://oauth2.googleapis.com/token"' "$key_file")
    
    # Create JWT header
    local header=$(echo -n '{"alg":"RS256","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
    
    # Create JWT claim set
    local now=$(date +%s)
    local exp=$((now + 3600))
    local claim=$(cat <<EOF
{
  "iss": "$client_email",
  "scope": "https://www.googleapis.com/auth/cloud-platform",
  "aud": "$token_uri",
  "iat": $now,
  "exp": $exp
}
EOF
)
    local claim_b64=$(echo -n "$claim" | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
    
    # Create signature
    local signing_input="${header}.${claim_b64}"
    local signature=$(echo -n "$signing_input" | openssl dgst -sha256 -sign <(echo "$private_key") | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
    
    # Create JWT
    local jwt="${signing_input}.${signature}"
    
    # Exchange JWT for access token
    local response=$(curl -s -X POST "$token_uri" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=$jwt")
    
    echo "$response" | jq -r '.access_token'
}

# Get access token
echo "Getting access token from service account..."
ACCESS_TOKEN=$(get_access_token)

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo "Error: Failed to get access token"
    exit 1
fi
echo "Got access token"

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
    
    # Refresh token if needed (tokens last 1 hour, so should be fine)
    RESULT=$(curl -s -X POST "$FETCH_URL" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"operationName\": \"$OPERATION_NAME\"}")
    
    DONE=$(echo "$RESULT" | jq -r '.done // false')
    
    if [ "$DONE" == "true" ]; then
        echo ""
        echo "Generation complete!"
        
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
