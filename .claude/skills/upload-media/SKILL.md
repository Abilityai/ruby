---
name: upload-media
description: Upload media to Cloudinary and get public URL
allowed-tools: Bash, Read
---

# Upload Media

Upload images, videos, or other media files to Cloudinary for use in social media posts.

## Quick Start

```bash
# Use Cloudinary MCP to upload
mcp__cloudinary-asset-mgmt__upload-asset
  source: "/path/to/file.png"
  resourceType: "image"

# Or use ToolSearch first if MCP not loaded
ToolSearch(query: "select:mcp__cloudinary-asset-mgmt__upload-asset")
```

## Usage

```
/upload-media <file path> [options]
```

**Parameters:**
- **file path**: Local file path or URL
- **--type**: image | video | raw (auto-detected if omitted)
- **--folder**: Cloudinary folder name
- **--public-id**: Custom public ID
- **--overwrite**: Overwrite existing file

**Examples:**
```
/upload-media 
/upload-media video.mp4 --folder=my-videos
/upload-media image.png --public-id=ai-framework-2025
```

## Workflow

### 1. Validate File

- Check file exists (if local path)
- Verify file size within limits
- Detect media type if not specified

### 2. Download if URL

If file is a URL:
```bash
curl -o /tmp/temp_media.ext "<url>"
```

### 3. Upload to Cloudinary

```bash
# Load the MCP tool first
ToolSearch(query: "select:mcp__cloudinary-asset-mgmt__upload-asset")

# Then upload
mcp__cloudinary-asset-mgmt__upload-asset
  source: "/path/to/file"
  resourceType: "image"  # or "video" or "raw"
  folder: "optional-folder-name"
  publicId: "optional-custom-id"
```

### 4. Return URLs

From upload response:
- **Public URL**: `https://res.cloudinary.com/dfs5yfioa/image/upload/v.../filename.png`
- **Secure URL**: Same with https
- **Thumbnail**: Add transformations like `c_thumb,w_200`

## File Size Limits

| Type | Max Size | Recommended |
|------|----------|-------------|
| Image | 10 MB | < 5 MB |
| Video | 100 MB | < 50 MB |
| Raw | 10 MB | - |

## Folder Organization

Suggested Cloudinary folder structure:
- `social-media/` - Posts and content
- `my-videos/` - HeyGen and produced videos
- `frameworks/` - Framework images
- `backup/` - Important media backup
- `temp/` - Temporary uploads

## Transformations

After upload, generate transformed URLs:

**Image:**
- Resize: `.../c_scale,w_800/image.png`
- Crop: `.../c_fill,w_1080,h_1920/image.png`
- Quality: `.../q_auto/image.png`
- Format: `.../f_auto/image.png`

**Video:**
- Quality: `.../q_auto/video.mp4`
- Format: `.../f_auto/video.mp4`
- Preview: `.../so_0,eo_3/video.mp4` (first 3 seconds)

## Response Format

```
Media uploaded successfully!

Public URL: https://res.cloudinary.com/dfs5yfioa/image/upload/v1699999999/filename.png
Secure URL: https://res.cloudinary.com/dfs5yfioa/image/upload/v1699999999/filename.png
Thumbnail: https://res.cloudinary.com/dfs5yfioa/image/upload/c_thumb,w_200/filename.png

File Details:
- Type: image/png
- Size: 245 KB
- Format: PNG
- Dimensions: 1920x1080
- Public ID: filename
```

## Use Cases

### Prepare Media for Social Posts
```
/upload-media screenshot.png
# Get URL -> Use in /post-now or /schedule-post
```

### Upload Video for Multi-Platform
```
/upload-media ai-video.mp4 --folder=social-media
# Get URL -> Post to Instagram, TikTok, LinkedIn
```

### Create Carousel (Multiple Images)
```
/upload-media image1.png --folder=carousel-topic
/upload-media image2.png --folder=carousel-topic
/upload-media image3.png --folder=carousel-topic
```

## Error Handling

| Error | Solution |
|-------|----------|
| File not found | Verify path, try absolute path |
| Upload fails | Check credentials in .mcp.json |
| File too large | Compress or split |
| Quota exceeded | Delete old files, check dashboard |

## Cloudinary Dashboard

Access: https://console.cloudinary.com/console/dfs5yfioa/

Features:
- View all uploaded files
- Organize into folders
- Apply transformations
- Monitor usage and quota
- Delete old files

## Integration with Other Skills

```
# Upload -> Post workflow
/upload-media screenshot.png
# Get URL
/post-now linkedin image "Check out this framework!" <URL>

# Upload -> Schedule workflow
/upload-media image.png
# Get URL
/schedule-post "tomorrow 9am" linkedin image "Post text" <URL>
```

## Tips

- **Organize**: Use folders for different content types
- **Name clearly**: Use descriptive public IDs
- **Clean up**: Delete unused media monthly
- **Monitor quota**: Check usage in dashboard
- **Test first**: Upload to temp folder for testing
