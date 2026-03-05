# Google Drive Path Mapping

**API Script**: `python3 .claude/scripts/google/google_drive.py <command> [args]`

<!-- Replace all YOUR_FOLDER_ID_HERE and YOUR_FILE_ID_HERE values with your actual Google Drive IDs -->
<!-- Use: python3 .claude/scripts/google/google_drive.py list <parent_folder_id> to discover IDs -->

## Folders

| Path | ID |
|------|-----|
| (root) | `YOUR_FOLDER_ID_HERE` |
| Content | `YOUR_FOLDER_ID_HERE` |
| Content/MM.YYYY | `YOUR_FOLDER_ID_HERE` |
| GeneratedShorts | `YOUR_FOLDER_ID_HERE` |
| AI Avatars | `YOUR_FOLDER_ID_HERE` |
| Intro_Templates | `YOUR_FOLDER_ID_HERE` |
| Prompts | `YOUR_FOLDER_ID_HERE` |
| Reference Photos | `YOUR_FOLDER_ID_HERE` |
| ClipShorts | `YOUR_FOLDER_ID_HERE` |
| Articles | `YOUR_FOLDER_ID_HERE` |
| Articles/drafts | `YOUR_FOLDER_ID_HERE` |
| Articles/published | `YOUR_FOLDER_ID_HERE` |
| Archive | `YOUR_FOLDER_ID_HERE` |
| Raw_Recordings | `YOUR_FOLDER_ID_HERE` |

## Files (Frequently Used)

| Path | ID |
|------|-----|
| brand_strategy_snapshot.md | `YOUR_FILE_ID_HERE` |
| Prompts/Twitter_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/LinkedIn_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/HeyGen_Video_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/Text_Post_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/Newsletter_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/LongForm_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/Community_Post_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/LinkedIn_Carousel_Tone_of_Voice_Profile.md | `YOUR_FILE_ID_HERE` |
| Prompts/Carousel_Styleguide.md | `YOUR_FILE_ID_HERE` |
| Prompts/Content_Type_Templates.md | `YOUR_FILE_ID_HERE` |
| Prompts/Broll_Style_Prompt.md | `YOUR_FILE_ID_HERE` |
| Prompts/Text_Overlay_Style_Profile.md | `YOUR_FILE_ID_HERE` |

## Intro Templates (video files)

**Use short intros by default** (~2 sec). Only use long intros (~8 sec) when explicitly requested.

### Short Intros - DEFAULT (~2 sec)

| Template Name | File ID |
|---------------|---------|
| grow_blur_short (DEFAULT) | `YOUR_FILE_ID_HERE` |
| smoke_waves_short | `YOUR_FILE_ID_HERE` |
| curves_short | `YOUR_FILE_ID_HERE` |
| radiate | `YOUR_FILE_ID_HERE` |
| radiate_blur | `YOUR_FILE_ID_HERE` |
| grow | `YOUR_FILE_ID_HERE` |

### Long Intros (~8 sec)

| Template Name | File ID |
|---------------|---------|
| grow_blur | `YOUR_FILE_ID_HERE` |
| smoke_waves | `YOUR_FILE_ID_HERE` |
| curves | `YOUR_FILE_ID_HERE` |
| silk | `YOUR_FILE_ID_HERE` |

### Outros (~8 sec)

| Template Name | File ID |
|---------------|---------|
| converging_circles | `YOUR_FILE_ID_HERE` |
| converging_v2 | `YOUR_FILE_ID_HERE` |
| curves_receding | `YOUR_FILE_ID_HERE` |
| curves_v2 | `YOUR_FILE_ID_HERE` |
| pulse_fade | `YOUR_FILE_ID_HERE` |

## Usage

When commands/agents reference paths like `Prompts/Twitter_Tone_of_Voice_Profile.md`:
1. Look up the ID from this mapping
2. Use the API to download: `python3 .claude/scripts/google/google_drive.py download <ID> /tmp/filename.md`
3. Read from `/tmp/filename.md`

For paths not in mapping, navigate using `list` command starting from nearest known folder.
