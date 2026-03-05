#!/bin/bash
# validate_media_url.sh - Validate media URL is accessible before scheduling
# Usage: ./validate_media_url.sh <url> [expected_type]
# Example: ./validate_media_url.sh "https://res.cloudinary.com/..." image

set -e

URL="$1"
EXPECTED_TYPE="${2:-any}"  # image, video, or any

if [ -z "$URL" ]; then
    echo "ERROR: URL required"
    echo "Usage: $0 <url> [image|video|any]"
    exit 1
fi

echo "Validating URL: $URL"
echo "Expected type: $EXPECTED_TYPE"
echo ""

# Check HTTP status
HTTP_RESPONSE=$(curl -sI "$URL" 2>/dev/null | head -20)
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | head -1 | awk '{print $2}')

if [ -z "$HTTP_STATUS" ]; then
    echo "ERROR: Could not connect to URL"
    exit 1
fi

echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" != "200" ]; then
    echo "ERROR: URL not accessible (expected 200, got $HTTP_STATUS)"

    if [ "$HTTP_STATUS" == "404" ]; then
        echo "HINT: File may have been deleted or URL expired (GoFile expires in 10-30 days)"
    elif [ "$HTTP_STATUS" == "403" ]; then
        echo "HINT: URL may require authentication or be private"
    fi
    exit 1
fi

# Check content type
CONTENT_TYPE=$(echo "$HTTP_RESPONSE" | grep -i "content-type:" | head -1 | cut -d' ' -f2 | tr -d '\r')
echo "Content-Type: $CONTENT_TYPE"

# Validate content type matches expected
if [ "$EXPECTED_TYPE" == "image" ]; then
    if [[ ! "$CONTENT_TYPE" =~ ^image/ ]]; then
        echo "WARNING: Expected image but got $CONTENT_TYPE"
    fi
elif [ "$EXPECTED_TYPE" == "video" ]; then
    if [[ ! "$CONTENT_TYPE" =~ ^video/ ]]; then
        echo "WARNING: Expected video but got $CONTENT_TYPE"
    fi
fi

# Check if GoFile URL (warn about expiration)
if [[ "$URL" =~ gofile\.io ]]; then
    echo ""
    echo "WARNING: GoFile URL detected!"
    echo "- GoFile URLs expire in 10-30 days"
    echo "- Do NOT use with Metricool (use Cloudinary instead)"
    echo "- Only use for Blotato posts scheduled ≤2 days out"
fi

# Check content length
CONTENT_LENGTH=$(echo "$HTTP_RESPONSE" | grep -i "content-length:" | head -1 | awk '{print $2}' | tr -d '\r')
if [ -n "$CONTENT_LENGTH" ]; then
    SIZE_MB=$((CONTENT_LENGTH / 1048576))
    echo "File Size: ${SIZE_MB}MB"

    if [ "$EXPECTED_TYPE" == "video" ] && [ "$SIZE_MB" -gt 100 ]; then
        echo ""
        echo "WARNING: Video is ${SIZE_MB}MB (>100MB Cloudinary free limit)"
        echo "- Cannot use with Metricool on Cloudinary free plan"
        echo "- Options: Compress video, use Blotato-only, or upgrade Cloudinary"
    fi
fi

echo ""
echo "VALIDATION PASSED"
exit 0
