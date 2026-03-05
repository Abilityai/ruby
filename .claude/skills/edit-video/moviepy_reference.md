# MoviePy Technical Reference Guide

## Version & Overview

**Current Version**: 2.1.2+ (approaching 2.2)
**Python Requirement**: 3.9+
**Key Note**: MoviePy v2.0+ introduced major breaking changes from v1. This guide covers v2.x API only.

### Recent Major Changes

- **v2.1.2**: Fixed critical transparency issues in compositing and rendering
- **v2.2**: Improved performance, FFmpeg v7 support, Pillow 11 support
- **Default bg_color changed** from None to (0,0,0) in CompositeVideoClip for performance

---

## Core Classes & Patterns

### VideoFileClip - Loading Videos

```python
from moviepy import VideoFileClip

# Basic loading
clip = VideoFileClip("video.mp4")

# With options
clip = VideoFileClip(
    "video.mp4",
    has_mask=True,               # If video contains alpha channel
    audio=True,                  # Load audio track
    target_resolution=(640, 480),# Pre-resize in ffmpeg
    resize_algorithm="bicubic",  # bicubic, bilinear, fast_bilinear
    audio_fps=44100,             # Audio sample rate
)

# CRITICAL: Must close to release file locks
clip.close()

# Better: Use context manager
with VideoFileClip("video.mp4") as clip:
    clip.write_videofile("output.mp4")
```

### AudioFileClip - Loading Audio

```python
from moviepy import AudioFileClip

audio = AudioFileClip(
    "audio.mp3",
    buffersize=200000,
    fps=44100,
)
audio.close()
```

### CompositeVideoClip - Stacking & Compositing

```python
from moviepy import CompositeVideoClip

clip1 = VideoFileClip("bg.mp4")
clip2 = VideoFileClip("overlay.mp4").with_start(2).with_position("center")

final = CompositeVideoClip(
    [clip1, clip2],
    size=(1920, 1080),
    bg_color=(0, 0, 0),          # Background color
    memoize_mask=True,           # Cache mask frames for speed
)
```

**CompositeVideoClip Mechanics**:
- Clips layered in order (later clips on top)
- Use `clip.layer_index` to control ordering (higher = on top)
- Clip `start` and `end` determine when it plays
- Duration = max(clip.end) for all clips
- Audio = auto-mixed from all clips' audio tracks

### CompositeAudioClip - Mixing Audio

```python
from moviepy import CompositeAudioClip, AudioFileClip

music = AudioFileClip("music.mp3")
sfx = AudioFileClip("sound.wav").with_start(10)

mixed_audio = CompositeAudioClip([
    music.with_volume_scaled(0.8),
    sfx.with_volume_scaled(0.15),
])

final_video = final_video.with_audio(mixed_audio)
```

### Concatenation

```python
from moviepy import concatenate_videoclips, concatenate_audioclips

final = concatenate_videoclips([clip1, clip2, clip3])
audio_final = concatenate_audioclips([audio1, audio2])
```

---

## Rendering & Encoding

### write_videofile()

```python
clip.write_videofile(
    "output.mp4",
    fps=None,                    # None = use clip.fps
    codec="libx264",             # Video codec
    preset="medium",             # ultrafast...medium...placebo
    audio_codec="aac",           # "aac", "libmp3lame"
    audio_bitrate="256k",
    ffmpeg_params=["-crf", "15", "-profile:v", "high"],
    logger="bar",
)
```

**Codec Selection**:

| Codec | Format | Use Case |
|-------|--------|----------|
| `libx264` | .mp4 | Default, web-friendly, H.264 |
| `libx265` | .mp4 | Better compression |
| `libvpx-vp9` | .webm | Transparency support |
| `png` | .avi | Lossless |

**Preset Speed vs Quality** (libx264):
- `ultrafast`: Fastest, largest files
- `medium`: Default balance
- `slow`, `slower`: Smaller files, much slower

**CRF Quality** (lower = better):
- 15-18: Near-lossless, large files
- 18-23: Good quality
- 23-28: Smaller files, visible compression

---

## Effects & Transformations

### Video Effects

```python
from moviepy import vfx

# Resizing
clip.with_effects([vfx.Resize(0.5)])          # 50% scale
clip.with_effects([vfx.Resize(width=800)])    # Height auto

# Resize method (direct, common pattern)
clip.resized((1280, 720))
clip.resized(0.5)

# Fading
clip.with_effects([vfx.FadeIn(1)])
clip.with_effects([vfx.FadeOut(1)])

# Speed
clip.with_effects([vfx.MultiplySpeed(2)])     # 2x speed

# Cropping
clip.with_effects([vfx.Crop(x1=100, y1=100, x2=500, y2=500)])
```

### Audio Effects

```python
from moviepy import afx

# Volume
audio.with_volume_scaled(0.5)                 # 50% volume

# Fading
audio.with_effects([afx.AudioFadeIn(1)])
audio.with_effects([afx.AudioFadeOut(1)])
```

---

## Timing & Positioning

### Setting Timing

```python
clip = clip.with_start(5)           # Start at 5 seconds
clip = clip.with_end(10)            # Stop at 10 seconds
clip = clip.with_duration(5)        # Set duration
clip = clip.subclipped(2, 8)        # Trim to 2-8 seconds
```

### Positioning

```python
clip = clip.with_position((100, 50))          # Absolute
clip = clip.with_position('center')           # Relative
clip = clip.with_position(('right', 'bottom'))

# Dynamic positioning
def move_right(t):
    return (100 + 50*t, 200)
clip = clip.with_position(move_right)
```

---

## Audio Handling

### Audio Basics

```python
video = VideoFileClip("video.mp4")
audio = video.audio                           # Get audio track
video_no_audio = video.without_audio()        # Remove audio

audio = audio.with_volume_scaled(0.8)         # Adjust volume
```

### Audio Mixing Pattern (Our Use Case)

```python
# Main video with original audio
main_clip = VideoFileClip("source.mp4")

# SFX clips positioned at specific times
sfx1 = AudioFileClip("whoosh.mp3").with_volume_scaled(0.15).with_start(10.0)
sfx2 = AudioFileClip("swoosh.mp3").with_volume_scaled(0.15).with_start(25.0)

# Mix all audio
audio_clips = [main_clip.audio]
audio_clips.extend([sfx1, sfx2])
final_audio = CompositeAudioClip(audio_clips)

# Apply to video
final_video = CompositeVideoClip([main_clip, broll1, broll2])
final_video = final_video.with_audio(final_audio)
```

---

## Performance Optimization

### Memory & Speed Tips

1. **Close clips when done**
   ```python
   with VideoFileClip("video.mp4") as clip:
       # Process
       pass
   # Auto-closed
   ```

2. **Pre-resize in FFmpeg**
   ```python
   clip = VideoFileClip("video.mp4", target_resolution=(1280, 720))
   ```

3. **Test on subclips first**
   ```python
   test = clip.subclipped(0, 5)
   test.write_videofile("test.mp4", preset="ultrafast")
   ```

4. **Use parallel threads**
   ```python
   clip.write_videofile("out.mp4", threads=4)
   ```

### Encoding Optimization

| Goal | Settings |
|------|----------|
| Speed (preview) | `preset="ultrafast"` |
| Quality | `preset="slow"`, `crf=15-18` |
| Balance | `preset="medium"` (default) |
| Web | `codec="libx264"`, `bitrate="5000k"` |

---

## Common Issues & Solutions

### File Locked

```python
# Always close clips
clip.close()

# Or use context managers
with VideoFileClip("video.mp4") as clip:
    pass
```

### Audio Out of Sync

```python
# Let MoviePy auto-composite audio
composite = CompositeVideoClip([clip1, clip2])
# Audio automatically mixed

# Don't manually separate unless needed
```

### Memory Issues

```python
# Reduce memoization
composite = CompositeVideoClip(clips, memoize_mask=False)

# Process in chunks for very long videos
```

---

## Our Video Editing Pattern

### B-Roll with SFX Insertion

```python
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip,
    CompositeVideoClip, CompositeAudioClip,
)

def execute_broll_edit(source_video, broll_edits, output_path):
    """Insert B-roll overlays with transition SFX."""

    # Load main video
    main_clip = VideoFileClip(source_video)
    main_size = main_clip.size

    video_clips = [main_clip]
    audio_clips = [main_clip.audio] if main_clip.audio else []

    for edit in broll_edits:
        at = edit['at']  # seconds
        duration = edit.get('duration', 3.0)
        asset_path = edit['asset_path']

        # Load B-roll
        if asset_path.endswith(('.png', '.jpg', '.jpeg')):
            broll = ImageClip(asset_path).with_duration(duration)
        else:
            broll = VideoFileClip(asset_path)
            if broll.duration > duration:
                broll = broll.subclipped(0, duration)

        # Resize and position
        broll = broll.resized(main_size)
        broll = broll.with_start(at)
        video_clips.append(broll)

        # Add SFX
        sfx_name = edit.get('transition_sfx', 'whoosh_fast_transition')
        sfx_volume = edit.get('sfx_volume', 0.15)
        sfx_offset = edit.get('sfx_offset', -0.15)

        sfx_path = resolve_sfx_path(sfx_name)
        if sfx_path:
            sfx = AudioFileClip(sfx_path)
            sfx = sfx.with_volume_scaled(sfx_volume)
            sfx = sfx.with_start(at + sfx_offset)
            audio_clips.append(sfx)

    # Composite
    final_video = CompositeVideoClip(video_clips, size=main_size)
    final_audio = CompositeAudioClip(audio_clips)
    final_video = final_video.with_audio(final_audio)

    # Render
    final_video.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='256k',
        fps=main_clip.fps,
        preset='medium',
        ffmpeg_params=['-crf', '15', '-profile:v', 'high'],
        logger='bar'
    )

    # Cleanup
    main_clip.close()
    final_video.close()
```

### Recommended SFX Settings

```python
{
    "transition_sfx": "whoosh_fast_transition",  # or swoosh_flying, sweep_small_fast
    "sfx_volume": 0.15,   # Subtle, doesn't overpower speech
    "sfx_offset": -0.15,  # Starts 150ms before B-roll appears
}
```

---

## API Quick Reference

| Task | Code |
|------|------|
| Load video | `VideoFileClip("file.mp4")` |
| Load audio | `AudioFileClip("file.mp3")` |
| Load image | `ImageClip("image.png").with_duration(3)` |
| Trim clip | `clip.subclipped(2, 10)` |
| Resize | `clip.resized((1280, 720))` or `clip.resized(0.5)` |
| Set volume | `audio.with_volume_scaled(0.15)` |
| Position | `clip.with_position("center")` |
| Set timing | `clip.with_start(5)` |
| Stack clips | `CompositeVideoClip([c1, c2])` |
| Mix audio | `CompositeAudioClip([a1, a2])` |
| Set audio | `video.with_audio(audio)` |
| Render | `clip.write_videofile("out.mp4")` |
| Close | `clip.close()` or use `with` statement |

---

*Reference for MoviePy 2.1.2+ - January 2026*
