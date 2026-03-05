#!/bin/bash

# Upload a file to GoFile and return the shareable URL
# Usage: ./upload_gofile.sh /path/to/file.mp4

set -e

# Load environment
RUBY_ROOT="${AGENT_ROOT}"

if [ -f "$RUBY_ROOT/.env" ]; then
    source "$RUBY_ROOT/.env"
fi

# Validate credentials
if [ -z "$GOFILE_API_TOKEN" ] || [ -z "$GOFILE_ROOT_FOLDER" ]; then
    echo "Error: GoFile credentials not set"
    echo "Required: GOFILE_API_TOKEN, GOFILE_ROOT_FOLDER in .env"
    exit 1
fi

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <file_path>"
    echo ""
    echo "Uploads a file to GoFile and returns the shareable URL."
    echo "URLs expire in 10-30 days - only use for content scheduled within 2 days."
    exit 1
fi

FILE_PATH="$1"

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

echo "Uploading: $FILE_PATH"
echo "Size: $(du -h "$FILE_PATH" | cut -f1)"

# Get upload server
echo "Getting upload server..."
SERVER=$(curl -s "https://api.gofile.io/servers" | jq -r '.data.servers[0].name')

if [ -z "$SERVER" ] || [ "$SERVER" == "null" ]; then
    echo "Error: Failed to get upload server"
    exit 1
fi

echo "Server: $SERVER"

# Upload file
echo "Uploading..."
RESPONSE=$(curl -s -X POST "https://$SERVER.gofile.io/contents/uploadfile" \
  -H "Authorization: Bearer $GOFILE_API_TOKEN" \
  -F "file=@$FILE_PATH" \
  -F "folderId=$GOFILE_ROOT_FOLDER")

# Check result
STATUS=$(echo "$RESPONSE" | jq -r '.status')

if [ "$STATUS" != "ok" ]; then
    echo "Error: Upload failed"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

# Extract URL
DOWNLOAD_URL=$(echo "$RESPONSE" | jq -r '.data.downloadPage')
FILE_ID=$(echo "$RESPONSE" | jq -r '.data.id')

echo ""
echo "Upload successful!"
echo "URL: $DOWNLOAD_URL"
echo "File ID: $FILE_ID"
echo ""
echo "WARNING: URL expires in 10-30 days."
echo "Only schedule content within 2 days of upload."

# Return just the URL for scripting
echo ""
echo "GOFILE_URL=$DOWNLOAD_URL"
