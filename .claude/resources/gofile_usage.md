# GoFile Integration Guide for Ruby

## Overview

GoFile is your temporary media hosting solution for social media posts. It provides:

- **Unlimited file size** (free tier)
- **10-30 day auto-deletion** (perfect for scheduled posts)
- **Simple API** with shareable URLs
- **No manual cleanup needed**

## CRITICAL: GoFile vs Cloudinary

| Use Case | GoFile | Cloudinary |
|----------|--------|------------|
| **Metricool posts** | NEVER | ALWAYS |
| **Blotato posts ≤2 days** | OK | OK |
| **Blotato posts >2 days** | NEVER | ALWAYS |
| **Videos >100MB** | OK (Blotato only) | Needs Plus plan |

**Why Metricool fails with GoFile:**
Metricool downloads media URLs when publishing. GoFile URLs expire in 10-30 days, causing "Error downloading the image: null" errors.

## Quick Start

### Option 1: Use Helper Scripts

**Bash:**
```bash
${AGENT_ROOT}/.claude/scripts/gofile_upload.sh /path/to/video.mp4
# Returns: https://gofile.io/d/XXXXXX
```

**Python:**
```bash
python3 ${AGENT_ROOT}/.claude/scripts/gofile_upload.py /path/to/video.mp4
# Returns: https://gofile.io/d/XXXXXX
```

### Option 2: Direct API Calls

**Step 1: Get Server**
```bash
SERVER=$(curl -s "https://api.gofile.io/servers" | jq -r '.data.servers[0].name')
```

**Step 2: Upload File**
```bash
curl -X POST "https://$SERVER.gofile.io/contents/uploadfile" \
  -H "Authorization: Bearer $GOFILE_API_TOKEN" \
  -F "file=@/path/to/video.mp4" \
  -F "folderId=cfe35c17-bb35-407e-946f-3069dfe2bb03" \
  | jq -r '.data.downloadPage'
```

## Account Details

- **Account ID**: `a69a0965-7876-4938-a709-eb15c1d7d9b5`
- **API Token**: `$GOFILE_API_TOKEN`
- **Root Folder**: `cfe35c17-bb35-407e-946f-3069dfe2bb03`
- **Email**: your-email@example.com
- **Tier**: Standard (free)

## Typical Workflow

### For Video Posts

1. **Generate/download video** to local file
   ```
   GeneratedShorts/Generated/video-2025-11-23.mp4
   ```

2. **Upload to GoFile**
   ```bash
   URL=$(python3 .claude/scripts/gofile_upload.py "GeneratedShorts/Generated/video-2025-11-23.mp4")
   ```

3. **Use URL with Blotato**
   ```bash
   # Schedule post with video URL
   curl -X POST https://api.blotato.com/v2/posts/schedule \
     -d "media_url=$URL" \
     -d "platforms[]=instagram"
   ```

4. **Archive local copy**
   ```bash
   mv GeneratedShorts/Generated/video-2025-11-23.mp4 \
      GeneratedShorts/Published/instagram/video-2025-11-23.mp4
   ```

5. **GoFile auto-deletes** in 10-30 days (no action needed)

### For Image Posts (Carousels)

1. **Generate images** with Nano Banana
   ```
   slide_01.png, slide_02.png, slide_03.png
   ```

2. **Upload all to GoFile**
   ```bash
   for slide in slide_*.png; do
     python3 .claude/scripts/gofile_upload.py "$slide"
   done
   ```

3. **Collect URLs** and post carousel to Blotato

## Python Integration Example

```python
import requests
import os

def upload_to_gofile(file_path):
    """Upload file and return shareable URL"""

    # Get server
    response = requests.get("https://api.gofile.io/servers")
    server = response.json()["data"]["servers"][0]["name"]

    # Upload file
    url = f"https://{server}.gofile.io/contents/uploadfile"
    headers = {"Authorization": "Bearer $GOFILE_API_TOKEN"}
    files = {"file": open(file_path, "rb")}
    data = {"folderId": "cfe35c17-bb35-407e-946f-3069dfe2bb03"}

    response = requests.post(url, headers=headers, files=files, data=data)
    return response.json()["data"]["downloadPage"]

# Usage
video_url = upload_to_gofile("GeneratedShorts/Generated/video.mp4")
print(f"Shareable URL: {video_url}")
```

## File Lifecycle

```
LOCAL FILE → GoFile Upload → Get URL → Use with Blotato → Post Publishes
    ↓                                                            ↓
Archive to                                              File auto-deletes
Published/                                              (10-30 days)
```

## Best Practices

1. **Upload immediately before posting/scheduling**
   - Don't upload weeks in advance
   - GoFile is for active content, not long-term storage

2. **Always archive local copies**
   - Move to `GeneratedShorts/Published/` after posting
   - GoFile files will expire

3. **Use URLs within days**
   - Perfect for scheduled posts (next 1-7 days)
   - Don't rely on links older than 30 days

4. **No cleanup needed**
   - Files auto-delete
   - Don't worry about manual removal

5. **Check file size**
   - Unlimited size on free tier
   - Large files (GB+) upload slower but work fine

## Troubleshooting

### Upload Fails
```bash
# Check account status
curl -s "https://api.gofile.io/accounts/a69a0965-7876-4938-a709-eb15c1d7d9b5" \
  -H "Authorization: Bearer $GOFILE_API_TOKEN" | jq .
```

### Check Storage Usage
```bash
# View current stats
curl -s "https://api.gofile.io/accounts/a69a0965-7876-4938-a709-eb15c1d7d9b5" \
  -H "Authorization: Bearer $GOFILE_API_TOKEN" \
  | jq '.data.statsCurrent'
```

### Slow Upload
- Large files (GB+) take time
- Server selection is automatic (EU or NA based on location)
- Use `-v` flag with curl to see upload progress

## Migration from Cloudinary

**Old workflow:**
```
Video → Cloudinary upload → Get URL → Post
```

**New workflow:**
```
Video → GoFile upload → Get URL → Post
```

**Key differences:**
- ✅ Simpler API (no complex transformations)
- ✅ Unlimited file size
- ✅ Auto-cleanup (no manual deletion)
- ❌ No image transformations (use Creatomate/Nano Banana instead)
- ❌ Temporary only (10-30 days vs permanent)

## When to Use vs. Not Use

**Use GoFile for:**
- Video posts to social media
- Image carousels
- Any media for scheduled posts
- Temporary sharing links

**Don't use GoFile for:**
- Long-term storage (use Google Drive)
- Permanent archives (use Published/ folder locally)
- Real-time transformations (use Creatomate/Nano Banana)
- Content older than 30 days

## Cost Comparison

**GoFile Free Tier:**
- Storage: Unlimited
- File size: Unlimited
- Retention: 10-30 days
- Uploads: 100,000 items
- Cost: $0/month

**vs. Cloudinary (previous):**
- Storage: 25 GB free
- Bandwidth: 25 GB/month free
- Transformations: Limited
- Cost: $0-89+/month

**Result:** Significant cost savings for temporary media hosting.
