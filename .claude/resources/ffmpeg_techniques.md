# FFmpeg Techniques for Video Editing

Technical reference for FFmpeg operations used in video editing workflows.

## Table of Contents

1. [Image to Video Conversion](#image-to-video-conversion)
2. [Transitions and Effects](#transitions-and-effects)
3. [Overlays and Compositing](#overlays-and-compositing)
4. [Audio Operations](#audio-operations)
5. [Concatenation](#concatenation)
6. [Scaling and Resolution](#scaling-and-resolution)
7. [Color and Visual Effects](#color-and-visual-effects)

---

## Image to Video Conversion

### Basic Static Image to Video

```bash
ffmpeg -y -loop 1 -i image.png -t 3.0 -c:v libx264 -pix_fmt yuv420p output.mp4
```

### Ken Burns Effect (Slow Zoom In)

Creates a subtle zoom from 1.0x to 1.05x over the duration:

```bash
ffmpeg -y -loop 1 -i image.png \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.0005,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1920x1080:fps=30" \
  -t 3.0 -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p output.mp4
```

**Parameters:**
- `zoom+0.0005` - Zoom increment per frame (smaller = slower zoom)
- `1.05` - Maximum zoom level
- `d=90` - Total frames (30fps * 3sec)
- `x/y` - Keep centered during zoom

### Ken Burns with Pan (Zoom + Move)

Zoom in while panning from left to right:

```bash
ffmpeg -y -loop 1 -i image.png \
  -vf "zoompan=z='min(zoom+0.001,1.1)':x='(iw-iw/zoom)*on/(90)':y='ih/2-(ih/zoom/2)':d=90:s=1920x1080:fps=30" \
  -t 3.0 -c:v libx264 -crf 18 -pix_fmt yuv420p output.mp4
```

### Zoom Out Effect

Start zoomed in, zoom out to full:

```bash
ffmpeg -y -loop 1 -i image.png \
  -vf "zoompan=z='if(lte(zoom,1.0),1.15,max(1.0,zoom-0.001))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1920x1080:fps=30" \
  -t 3.0 -c:v libx264 -crf 18 -pix_fmt yuv420p output.mp4
```

### Slide Effect (Pan Without Zoom)

Pan from left to right across a wider image:

```bash
ffmpeg -y -loop 1 -i wide_image.png \
  -vf "zoompan=z=1:x='(iw-ow)*on/90':y=0:d=90:s=1920x1080:fps=30" \
  -t 3.0 -c:v libx264 -crf 18 -pix_fmt yuv420p output.mp4
```

---

## Transitions and Effects

### Fade In from Black

```bash
ffmpeg -i input.mp4 -vf "fade=t=in:st=0:d=0.5" -c:a copy output.mp4
```

### Fade Out to Black

```bash
ffmpeg -i input.mp4 -vf "fade=t=out:st=2.5:d=0.5" -c:a copy output.mp4
```

### Combined Fade In + Fade Out

```bash
ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5" \
  -c:a copy output.mp4
```

### Alpha Fade (for Overlays)

Fade transparency rather than brightness:

```bash
# Fade alpha channel in
fade=t=in:st=0:d=0.5:alpha=1

# Fade alpha channel out
fade=t=out:st=2.5:d=0.5:alpha=1
```

### Crossfade Between Two Clips

Using xfade filter (FFmpeg 4.3+):

```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=2.5[v]" \
  -map "[v]" -c:v libx264 output.mp4
```

**Available xfade transitions:**
- `fade` - Standard crossfade
- `dissolve` - Dissolve effect
- `wipeleft`, `wiperight`, `wipeup`, `wipedown` - Wipe transitions
- `slideleft`, `slideright`, `slideup`, `slidedown` - Slide transitions
- `circleopen`, `circleclose` - Circle reveal/close
- `rectcrop` - Rectangle crop
- `distance` - Distance-based dissolve
- `smoothleft`, `smoothright` - Smooth slide
- `hlwind`, `hrwind` - Wind effect

### Blur Effect

```bash
# Gaussian blur
ffmpeg -i input.mp4 -vf "gblur=sigma=10" output.mp4

# Box blur (faster)
ffmpeg -i input.mp4 -vf "boxblur=5:1" output.mp4
```

### Animated Blur (Blur In/Out)

```bash
# Blur fades out over first 1 second
ffmpeg -i input.mp4 \
  -vf "gblur=sigma='max(0,20*(1-t))':enable='lt(t,1)'" \
  output.mp4
```

### Glow/Bloom Effect

```bash
# Create glow by blending blurred version
ffmpeg -i input.mp4 \
  -filter_complex "[0:v]split[a][b];[b]gblur=sigma=30[blur];[a][blur]blend=all_mode=screen:all_opacity=0.3" \
  output.mp4
```

---

## Overlays and Compositing

### Basic Overlay (Centered)

```bash
ffmpeg -i background.mp4 -i overlay.png \
  -filter_complex "[0:v][1:v]overlay=x=(W-w)/2:y=(H-h)/2" \
  output.mp4
```

### Overlay with Timing (Enable Between Timestamps)

```bash
ffmpeg -i background.mp4 -i overlay.png \
  -filter_complex "[0:v][1:v]overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,5,8)'" \
  output.mp4
```

### Overlay with Fade In/Out

```bash
ffmpeg -i background.mp4 -loop 1 -i overlay.png \
  -filter_complex "[1:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st=2.5:d=0.5:alpha=1[img];[0:v][img]overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,5,8)'" \
  output.mp4
```

### Picture-in-Picture (PIP)

```bash
# Small video in bottom-right corner
ffmpeg -i main.mp4 -i pip.mp4 \
  -filter_complex "[1:v]scale=320:-1[pip];[0:v][pip]overlay=W-w-20:H-h-20" \
  output.mp4
```

### Border/Frame Around Image

```bash
ffmpeg -i image.png \
  -vf "pad=width=iw+20:height=ih+20:x=10:y=10:color=0x3B82F6" \
  framed.png
```

### Replace Video Segment with B-roll

```bash
# 1. Extract segments
ffmpeg -i main.mp4 -ss 0 -t 5 -c copy pre.mp4
ffmpeg -i main.mp4 -ss 8 -c copy post.mp4

# 2. Scale B-roll to match
ffmpeg -i broll.mp4 -t 3 \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
  broll_scaled.mp4

# 3. Extract original audio for B-roll section
ffmpeg -i main.mp4 -ss 5 -t 3 -vn -c:a aac audio.aac

# 4. Combine B-roll with original audio
ffmpeg -i broll_scaled.mp4 -i audio.aac -c:v copy -c:a copy broll_with_audio.mp4

# 5. Concatenate
echo "file 'pre.mp4'" > concat.txt
echo "file 'broll_with_audio.mp4'" >> concat.txt
echo "file 'post.mp4'" >> concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c:v libx264 -crf 18 -c:a aac output.mp4
```

---

## Audio Operations

### Extract Audio

```bash
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 2 audio.wav
```

### Remove Audio

```bash
ffmpeg -i video.mp4 -an -c:v copy output.mp4
```

### Mix Audio Tracks

```bash
ffmpeg -i video.mp4 -i background_music.mp3 \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]" \
  -map 0:v -map "[a]" output.mp4
```

### Adjust Audio Volume

```bash
# Set volume to 50%
ffmpeg -i video.mp4 -af "volume=0.5" output.mp4

# Boost by 6dB
ffmpeg -i video.mp4 -af "volume=6dB" output.mp4
```

### Audio Fade In/Out

```bash
ffmpeg -i audio.mp3 \
  -af "afade=t=in:st=0:d=1,afade=t=out:st=9:d=1" \
  output.mp3
```

---

## Concatenation

### Simple Concatenation (Same Codec)

```bash
echo "file 'clip1.mp4'" > concat.txt
echo "file 'clip2.mp4'" >> concat.txt
echo "file 'clip3.mp4'" >> concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
```

### Concatenation with Re-encoding (Different Sources)

**IMPORTANT**: Always re-encode when concatenating clips from different sources to avoid freeze/blink issues.

```bash
ffmpeg -f concat -safe 0 -i concat.txt \
  -c:v libx264 -crf 18 -preset fast \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output.mp4
```

### Concatenation with Crossfade

```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5;[0:a][1:a]acrossfade=d=0.5" \
  output.mp4
```

---

## Scaling and Resolution

### Scale to Specific Resolution

```bash
# Exact size (may distort)
ffmpeg -i input.mp4 -vf "scale=1920:1080" output.mp4

# Maintain aspect ratio, fit within bounds
ffmpeg -i input.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease" output.mp4

# Fit and pad with black bars
ffmpeg -i input.mp4 \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
  output.mp4
```

### Horizontal to Vertical (with Blur Background)

```bash
ffmpeg -i horizontal.mp4 \
  -filter_complex "[0:v]split[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=50[blurbg];[fg]scale=1080:-1[scaled];[blurbg][scaled]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 vertical.mp4
```

### Horizontal to Vertical (with Crop)

```bash
ffmpeg -i horizontal.mp4 \
  -vf "scale=1920:-1,crop=1080:1920" \
  -c:v libx264 -crf 18 vertical.mp4
```

### Match Framerate

```bash
# Convert 30fps B-roll to match 29.97fps source
ffmpeg -i broll.mp4 -vf "fps=30000/1001" -c:v libx264 output.mp4
```

---

## Color and Visual Effects

### Color Grading Presets

```bash
# Vibrant (social media)
ffmpeg -i input.mp4 -vf "vibrance=intensity=0.3,eq=contrast=1.08" output.mp4

# High contrast + saturation
ffmpeg -i input.mp4 -vf "eq=contrast=1.15:saturation=1.2:brightness=0.02" output.mp4

# Warm tone
ffmpeg -i input.mp4 \
  -vf "colorbalance=rs=0.1:gs=0.05:bs=-0.1:rm=0.08:gm=0.02:bm=-0.05,eq=saturation=1.1:contrast=1.05" \
  output.mp4
```

### Vignette Effect

```bash
ffmpeg -i input.mp4 -vf "vignette=PI/4" output.mp4
```

### Black and White

```bash
ffmpeg -i input.mp4 -vf "hue=s=0" output.mp4
```

### Color Tint

```bash
# Blue tint
ffmpeg -i input.mp4 -vf "colorbalance=bs=0.3:bm=0.2:bh=0.1" output.mp4
```

---

## Useful Patterns

### Get Video Properties

```bash
# Resolution
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 video.mp4

# Framerate
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 video.mp4

# Duration
ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4
```

### Timestamp Formats

```bash
# Seconds: -ss 5.5
# HH:MM:SS: -ss 00:00:05.5
# Frames (at 30fps): -ss 165 (for 5.5 seconds)
```

### Safe Encoding Settings

For maximum compatibility:

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -preset fast -crf 18 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p \
  -movflags +faststart \
  output.mp4
```

---

## Common Issues and Solutions

### Freeze/Blink at Concatenation Points
**Cause**: Mismatched codecs, framerates, or keyframe intervals
**Solution**: Re-encode all segments with identical parameters before concatenation

### Audio Sync Issues
**Cause**: Variable framerate source or audio sample rate mismatch
**Solution**: Normalize framerate and audio sample rate before processing

### Green Frames
**Cause**: Corrupt keyframes or incompatible pixel format
**Solution**: Use `-pix_fmt yuv420p` and re-encode

### File Size Too Large
**Solution**: Increase CRF value (18-23 is good balance), use `preset slow`
