#!/usr/bin/env python3
"""
Google Drive management via Service Account (Ruby Agent)

Usage:
  python google_drive.py list [folder_id]
  python google_drive.py upload local_path [remote_name] [folder_id]
  python google_drive.py upload-folder local_folder parent_folder_id [--recursive]
  python google_drive.py download file_id_or_name local_path
  python google_drive.py mkdir folder_name [parent_folder_id]
  python google_drive.py ensure-path path/to/folder [base_folder_id]
  python google_drive.py move file_id new_parent_id
  python google_drive.py delete file_id
  python google_drive.py info file_id
  python google_drive.py find name [parent_folder_id]

Examples:
  python google_drive.py list
  python google_drive.py ensure-path "Content/01.2026/Video_Topic"
  python google_drive.py upload video.mp4 "original.mp4" <folder_id>
  python google_drive.py upload-folder "/tmp/Generated Content_2026-02-11" <parent_id>
  python google_drive.py find "transcript.md"
"""

import sys
import os
import io
import argparse
from pathlib import Path

# Service account configuration
SCRIPT_DIR = Path(__file__).parent
SERVICE_ACCOUNT_PATH = SCRIPT_DIR / "trinity-vertex-ai-account.json"

# Shared Drive Shared Drive
ROOT_FOLDER_ID = "0AEyxdy5hKtydUk9PVA"

# Set credentials
if SERVICE_ACCOUNT_PATH.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_PATH)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive']


def get_service():
    """Authenticate and return Drive service."""
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_PATH), scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def list_files(folder_id=None, recursive=False):
    """List files in folder."""
    folder_id = folder_id or ROOT_FOLDER_ID
    service = get_service()

    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, size, modifiedTime)",
        orderBy="name",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    items = results.get('files', [])
    if not items:
        print("No files found.")
        return []

    print(f"Files in folder ({len(items)}):")
    for item in items:
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        size = item.get('size', '-')
        icon = "D" if is_folder else "F"
        print(f"  [{icon}] {item['name']}")
        print(f"      ID: {item['id']}")
        if not is_folder and size != '-':
            print(f"      Size: {int(size):,} bytes")

    return items


def upload_file(local_path, remote_name=None, folder_id=None):
    """Upload a local file to Drive."""
    folder_id = folder_id or ROOT_FOLDER_ID
    local_path = Path(local_path)

    if not local_path.exists():
        print(f"Error: File not found: {local_path}")
        return None

    remote_name = remote_name or local_path.name
    service = get_service()

    file_metadata = {
        'name': remote_name,
        'parents': [folder_id]
    }

    media = MediaFileUpload(str(local_path), resumable=True)

    print(f"Uploading: {local_path.name} -> {remote_name}")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink',
        supportsAllDrives=True
    ).execute()

    print(f"Uploaded successfully!")
    print(f"  ID: {file.get('id')}")
    print(f"  Link: {file.get('webViewLink')}")
    return file


def upload_folder(local_folder, parent_folder_id, recursive=False):
    """
    Upload an entire folder to Google Drive.

    Args:
        local_folder: Path to local folder to upload
        parent_folder_id: ID of parent folder on Drive
        recursive: If True, also upload subfolders recursively

    Returns:
        Dict with folder_id and upload statistics
    """
    local_folder = Path(local_folder)

    if not local_folder.exists():
        print(f"Error: Folder not found: {local_folder}")
        return None

    if not local_folder.is_dir():
        print(f"Error: Not a directory: {local_folder}")
        return None

    # Create the folder on Drive
    folder_name = local_folder.name
    print(f"Creating folder on Drive: {folder_name}")
    drive_folder = create_folder(folder_name, parent_folder_id)
    drive_folder_id = drive_folder['id']

    # Track statistics
    stats = {
        'folder_id': drive_folder_id,
        'folder_name': folder_name,
        'files_uploaded': 0,
        'files_failed': 0,
        'subfolders_uploaded': 0,
        'total_bytes': 0,
    }

    # Get all items in the folder
    items = list(local_folder.iterdir())
    files = [f for f in items if f.is_file()]
    subfolders = [f for f in items if f.is_dir()]

    # Upload files
    print(f"Uploading {len(files)} file(s)...")
    for file_path in sorted(files):
        try:
            result = upload_file(str(file_path), file_path.name, drive_folder_id)
            if result:
                stats['files_uploaded'] += 1
                stats['total_bytes'] += file_path.stat().st_size
            else:
                stats['files_failed'] += 1
        except Exception as e:
            print(f"  Error uploading {file_path.name}: {e}")
            stats['files_failed'] += 1

    # Handle subfolders if recursive
    if recursive and subfolders:
        print(f"Uploading {len(subfolders)} subfolder(s)...")
        for subfolder in sorted(subfolders):
            sub_result = upload_folder(str(subfolder), drive_folder_id, recursive=True)
            if sub_result:
                stats['subfolders_uploaded'] += 1
                stats['files_uploaded'] += sub_result['files_uploaded']
                stats['files_failed'] += sub_result['files_failed']
                stats['total_bytes'] += sub_result['total_bytes']

    # Print summary
    print(f"\n{'='*50}")
    print(f"Upload Complete: {folder_name}")
    print(f"{'='*50}")
    print(f"  Drive Folder ID: {drive_folder_id}")
    print(f"  Files uploaded: {stats['files_uploaded']}")
    if stats['files_failed'] > 0:
        print(f"  Files failed: {stats['files_failed']}")
    if stats['subfolders_uploaded'] > 0:
        print(f"  Subfolders: {stats['subfolders_uploaded']}")
    print(f"  Total size: {stats['total_bytes']:,} bytes")
    print(f"  Drive link: https://drive.google.com/drive/folders/{drive_folder_id}")

    return stats


def download_file(file_id_or_name, local_path):
    """Download a file from Drive."""
    service = get_service()

    # If it looks like a name, search for it
    if not file_id_or_name.startswith('1') or len(file_id_or_name) < 20:
        query = f"name = '{file_id_or_name}' and trashed=false"
        results = service.files().list(
            q=query, fields="files(id, name)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])
        if not items:
            print(f"File '{file_id_or_name}' not found.")
            return False
        file_id = items[0]['id']
        print(f"Found file: {items[0]['name']} (ID: {file_id})")
    else:
        file_id = file_id_or_name

    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    print(f"Downloading to: {local_path}")
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"  Progress: {int(status.progress() * 100)}%")

    with open(local_path, 'wb') as f:
        f.write(fh.getbuffer())

    print(f"Downloaded successfully!")
    return True


def create_folder(folder_name, parent_id=None):
    """Create a folder in Drive."""
    parent_id = parent_id or ROOT_FOLDER_ID
    service = get_service()

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }

    folder = service.files().create(
        body=file_metadata,
        fields='id, name, webViewLink',
        supportsAllDrives=True
    ).execute()

    print(f"Created folder: {folder_name}")
    print(f"  ID: {folder.get('id')}")
    return folder


def delete_file(file_id, permanent=False):
    """Delete (trash) a file or folder from Drive."""
    service = get_service()
    if permanent:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        print(f"Permanently deleted: {file_id}")
    else:
        service.files().update(
            fileId=file_id,
            body={'trashed': True},
            supportsAllDrives=True
        ).execute()
        print(f"Trashed: {file_id}")
    return True


def get_file_info(file_id):
    """Get detailed info about a file."""
    service = get_service()
    file = service.files().get(
        fileId=file_id,
        fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink, parents",
        supportsAllDrives=True
    ).execute()

    print(f"File: {file.get('name')}")
    print(f"  ID: {file.get('id')}")
    print(f"  Type: {file.get('mimeType')}")
    print(f"  Size: {file.get('size', 'N/A')} bytes")
    print(f"  Created: {file.get('createdTime')}")
    print(f"  Modified: {file.get('modifiedTime')}")
    print(f"  Link: {file.get('webViewLink')}")
    return file


def move_file(file_id, new_parent_id):
    """Move a file to a new parent folder."""
    service = get_service()

    # Get current parents
    file = service.files().get(
        fileId=file_id,
        fields='parents, name',
        supportsAllDrives=True
    ).execute()

    previous_parents = ",".join(file.get('parents', []))

    # Move the file
    file = service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields='id, name, parents',
        supportsAllDrives=True
    ).execute()

    print(f"Moved: {file.get('name')}")
    print(f"  ID: {file.get('id')}")
    print(f"  New parent: {new_parent_id}")
    return file


def find_folder_by_name(folder_name, parent_id=None):
    """Find a folder by name in a parent folder."""
    parent_id = parent_id or ROOT_FOLDER_ID
    service = get_service()

    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    items = results.get('files', [])
    if items:
        return items[0]['id']
    return None


def find_file_by_name(file_name, parent_id=None):
    """Find a file by name in a parent folder or entire drive."""
    service = get_service()

    if parent_id:
        query = f"name = '{file_name}' and '{parent_id}' in parents and trashed=false"
    else:
        query = f"name = '{file_name}' and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, parents)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="drive",
        driveId=ROOT_FOLDER_ID
    ).execute()

    items = results.get('files', [])
    if not items:
        print(f"No files found matching: {file_name}")
        return []

    print(f"Found {len(items)} file(s) matching '{file_name}':")
    for item in items:
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        icon = "D" if is_folder else "F"
        print(f"  [{icon}] {item['name']}")
        print(f"      ID: {item['id']}")

    return items


def ensure_path(path, base_folder_id=None):
    """
    Ensure a path exists, creating folders as needed.

    Args:
        path: Path like "Content/01.2026/Video_Topic"
        base_folder_id: Starting folder ID (defaults to ROOT_FOLDER_ID)

    Returns:
        The ID of the final folder in the path
    """
    base_folder_id = base_folder_id or ROOT_FOLDER_ID
    service = get_service()

    parts = path.strip('/').split('/')
    current_parent = base_folder_id

    for part in parts:
        # Check if folder exists
        folder_id = find_folder_by_name(part, current_parent)

        if folder_id:
            print(f"  Found: {part} (ID: {folder_id})")
            current_parent = folder_id
        else:
            # Create folder
            print(f"  Creating: {part}")
            folder = create_folder(part, current_parent)
            current_parent = folder['id']

    print(f"Path ready: {path}")
    print(f"  Final folder ID: {current_parent}")
    return current_parent


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == 'list':
        folder_id = sys.argv[2] if len(sys.argv) > 2 else None
        list_files(folder_id)

    elif action == 'upload':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py upload local_path [remote_name] [folder_id]")
            sys.exit(1)
        local_path = sys.argv[2]
        remote_name = sys.argv[3] if len(sys.argv) > 3 else None
        folder_id = sys.argv[4] if len(sys.argv) > 4 else None
        upload_file(local_path, remote_name, folder_id)

    elif action == 'upload-folder':
        if len(sys.argv) < 4:
            print("Usage: python google_drive.py upload-folder local_folder parent_folder_id [--recursive]")
            sys.exit(1)
        local_folder = sys.argv[2]
        parent_folder_id = sys.argv[3]
        recursive = '--recursive' in sys.argv
        upload_folder(local_folder, parent_folder_id, recursive)

    elif action == 'download':
        if len(sys.argv) < 4:
            print("Usage: python google_drive.py download file_id_or_name local_path")
            sys.exit(1)
        download_file(sys.argv[2], sys.argv[3])

    elif action == 'mkdir':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py mkdir folder_name [parent_folder_id]")
            sys.exit(1)
        folder_name = sys.argv[2]
        parent_id = sys.argv[3] if len(sys.argv) > 3 else None
        create_folder(folder_name, parent_id)

    elif action == 'ensure-path':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py ensure-path path/to/folder [base_folder_id]")
            sys.exit(1)
        path = sys.argv[2]
        base_folder_id = sys.argv[3] if len(sys.argv) > 3 else None
        ensure_path(path, base_folder_id)

    elif action == 'move':
        if len(sys.argv) < 4:
            print("Usage: python google_drive.py move file_id new_parent_id")
            sys.exit(1)
        move_file(sys.argv[2], sys.argv[3])

    elif action == 'delete':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py delete file_id")
            sys.exit(1)
        delete_file(sys.argv[2])

    elif action == 'info':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py info file_id")
            sys.exit(1)
        get_file_info(sys.argv[2])

    elif action == 'find':
        if len(sys.argv) < 3:
            print("Usage: python google_drive.py find name [parent_folder_id]")
            sys.exit(1)
        file_name = sys.argv[2]
        parent_id = sys.argv[3] if len(sys.argv) > 3 else None
        find_file_by_name(file_name, parent_id)

    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)
