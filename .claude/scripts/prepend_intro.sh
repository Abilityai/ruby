#!/bin/bash
# prepend_intro.sh - Prepend branded intro video to main video
#
# Usage: prepend_intro.sh <main_video> <output_video> [intro_template]
#
# Arguments:
#   main_video    - Path to the main video file
#   output_video  - Path for the output (combined) video
#   intro_template - (optional) Intro template name. Default: grow_blur
#
# Available intro templates (stored in Google Drive Intro_Templates folder):
#   grow_blur     - Growing circles with blur (2s) - DEFAULT, recommended
#   radiate_blur  - Radiating light with blur (2s)
#   grow          - Expanding blobs, sharper (3s)
#   radiate       - Radiating light, sharper (3s)
#   smoke_waves   - Horizontal smoke waves (2s)
#   curves        - Flowing gradient curves (2s)
#   silk          - Abstract silk shapes (2s)
#
# Example:
#   ./prepend_intro.sh ~/video.mp4 ~/video_with_intro.mp4
#   ./prepend_intro.sh ~/video.mp4 ~/video_with_intro.mp4 smoke_waves

set -e

# Script directory (for finding google_drive.py)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GDRIVE_SCRIPT="$SCRIPT_DIR/google/google_drive.py"

# Default template
DEFAULT_TEMPLATE="grow_blur"

# Function to get template file ID
get_template_id() {
    case "$1" in
        grow_blur)    echo "YOUR_INTRO_GROW_BLUR_ID" ;;
        radiate_blur) echo "1wxZTqR_ODzv2N0HBoW7z9CcMoSHh8c7l" ;;
        grow)         echo "YOUR_INTRO_GROW_ID" ;;
        radiate)      echo "YOUR_INTRO_RADIATE_ID" ;;
        smoke_waves)  echo "YOUR_INTRO_SMOKE_WAVES_ID" ;;
        curves)       echo "YOUR_INTRO_CURVES_ID" ;;
        silk)         echo "YOUR_INTRO_SILK_ID" ;;
        *)            echo "" ;;
    esac
}

# Parse arguments
MAIN_VIDEO="$1"
OUTPUT_VIDEO="$2"
INTRO_TEMPLATE="${3:-$DEFAULT_TEMPLATE}"

# Validation
if [ -z "$MAIN_VIDEO" ] || [ -z "$OUTPUT_VIDEO" ]; then
    echo "Usage: prepend_intro.sh <main_video> <output_video> [intro_template]"
    echo ""
    echo "Available templates:"
    echo "  grow_blur (DEFAULT)"
    echo "  radiate_blur"
    echo "  grow"
    echo "  radiate"
    echo "  smoke_waves"
    echo "  curves"
    echo "  silk"
    exit 1
fi

if [ ! -f "$MAIN_VIDEO" ]; then
    echo "Error: Main video not found: $MAIN_VIDEO"
    exit 1
fi

# Get intro file ID
INTRO_FILE_ID=$(get_template_id "$INTRO_TEMPLATE")
if [ -z "$INTRO_FILE_ID" ]; then
    echo "Error: Unknown template '$INTRO_TEMPLATE'"
    echo "Available templates: grow_blur, radiate_blur, grow, radiate, smoke_waves, curves, silk"
    exit 1
fi

# Check for Google Drive script
if [ ! -f "$GDRIVE_SCRIPT" ]; then
    echo "Error: Google Drive script not found: $GDRIVE_SCRIPT"
    exit 1
fi

# Create temp directory for intermediate files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Download intro from Google Drive
INTRO_PATH="$TEMP_DIR/intro_${INTRO_TEMPLATE}.mp4"
echo "Downloading intro template from Google Drive..."
echo "  Template: $INTRO_TEMPLATE"

python3 "$GDRIVE_SCRIPT" download "$INTRO_FILE_ID" "$INTRO_PATH" 2>&1 | grep -v "^$" || {
    echo "Error: Failed to download intro template from Google Drive"
    exit 1
}

if [ ! -f "$INTRO_PATH" ]; then
    echo "Error: Intro file download failed"
    exit 1
fi

echo "Prepending intro to video..."
echo "  Main video: $MAIN_VIDEO"
echo "  Output: $OUTPUT_VIDEO"

# Get main video codec info
MAIN_CODEC=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$MAIN_VIDEO")
MAIN_WIDTH=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$MAIN_VIDEO")
MAIN_HEIGHT=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$MAIN_VIDEO")
MAIN_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$MAIN_VIDEO")

echo "  Main video: ${MAIN_WIDTH}x${MAIN_HEIGHT} @ $MAIN_FPS fps ($MAIN_CODEC)"

# Re-encode intro to match main video specs (resolution, fps, codec)
echo "  Re-encoding intro to match main video..."
INTRO_NORMALIZED="$TEMP_DIR/intro_normalized.mp4"

ffmpeg -y -i "$INTRO_PATH" \
    -vf "scale=${MAIN_WIDTH}:${MAIN_HEIGHT}:force_original_aspect_ratio=decrease,pad=${MAIN_WIDTH}:${MAIN_HEIGHT}:(ow-iw)/2:(oh-ih)/2" \
    -r "$MAIN_FPS" \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 128k \
    -pix_fmt yuv420p \
    "$INTRO_NORMALIZED" 2>/dev/null

# Also normalize main video for consistent concat
echo "  Normalizing main video..."
MAIN_NORMALIZED="$TEMP_DIR/main_normalized.mp4"

ffmpeg -y -i "$MAIN_VIDEO" \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 128k \
    -pix_fmt yuv420p \
    "$MAIN_NORMALIZED" 2>/dev/null

# Create concat file
CONCAT_FILE="$TEMP_DIR/concat.txt"
echo "file '$INTRO_NORMALIZED'" > "$CONCAT_FILE"
echo "file '$MAIN_NORMALIZED'" >> "$CONCAT_FILE"

# Concatenate
echo "  Concatenating videos..."
ffmpeg -y -f concat -safe 0 -i "$CONCAT_FILE" \
    -c copy \
    "$OUTPUT_VIDEO" 2>/dev/null

# Get output duration
OUTPUT_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_VIDEO")
OUTPUT_SIZE=$(ls -lh "$OUTPUT_VIDEO" | awk '{print $5}')

echo ""
echo "Done!"
echo "  Output: $OUTPUT_VIDEO"
echo "  Duration: ${OUTPUT_DURATION}s"
echo "  Size: $OUTPUT_SIZE"
