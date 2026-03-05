#!/usr/bin/env python3
"""
Manage B-roll and graphics asset library.

Commands:
- search: Find assets by tags/keywords
- list: List assets by type/category
- add: Add new asset to manifest
- info: Get asset details
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_manifest_path() -> Path:
    """Get path to asset manifest."""
    # Skill directory is parent of scripts/
    skill_dir = Path(__file__).parent.parent
    return skill_dir / 'assets' / 'manifest.json'


def load_manifest() -> dict:
    """Load asset manifest."""
    path = get_manifest_path()
    if path.exists():
        return json.loads(path.read_text())
    return {
        'version': '1.0',
        'assets': [],
        'categories': {
            'broll': ['tech', 'business', 'abstract'],
            'graphic': ['lower_third', 'transition', 'overlay'],
            'audio': ['sfx', 'music', 'ambient']
        },
        'tag_synonyms': {}
    }


def save_manifest(manifest: dict):
    """Save asset manifest."""
    path = get_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))


def expand_keywords(keywords: list, manifest: dict) -> set:
    """Expand keywords using synonyms."""
    expanded = set(k.lower() for k in keywords)

    for kw in list(expanded):
        for canonical, synonyms in manifest.get('tag_synonyms', {}).items():
            if kw == canonical.lower() or kw in [s.lower() for s in synonyms]:
                expanded.add(canonical.lower())
                expanded.update(s.lower() for s in synonyms)

    return expanded


def search_assets(keywords: list, asset_type: Optional[str] = None, manifest: Optional[dict] = None) -> list:
    """Search assets by keywords."""
    if manifest is None:
        manifest = load_manifest()

    expanded = expand_keywords(keywords, manifest)

    results = []
    for asset in manifest.get('assets', []):
        # Filter by type if specified
        if asset_type and asset.get('type') != asset_type:
            continue

        # Score by tag matches
        asset_tags = set(t.lower() for t in asset.get('tags', []))
        score = len(expanded.intersection(asset_tags))

        if score > 0:
            results.append({
                **asset,
                'match_score': score,
                'matched_tags': list(expanded.intersection(asset_tags))
            })

    # Sort by score descending
    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results


def list_assets(asset_type: Optional[str] = None, category: Optional[str] = None, manifest: Optional[dict] = None) -> list:
    """List assets, optionally filtered."""
    if manifest is None:
        manifest = load_manifest()

    results = []
    for asset in manifest.get('assets', []):
        if asset_type and asset.get('type') != asset_type:
            continue
        if category and asset.get('category') != category:
            continue
        results.append(asset)

    return results


def get_asset_info(asset_id: str, manifest: Optional[dict] = None) -> Optional[dict]:
    """Get asset by ID."""
    if manifest is None:
        manifest = load_manifest()

    for asset in manifest.get('assets', []):
        if asset.get('id') == asset_id:
            return asset
    return None


def get_video_info(video_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        stream = data.get('streams', [{}])[0]
        format_info = data.get('format', {})

        return {
            'width': stream.get('width'),
            'height': stream.get('height'),
            'duration': float(format_info.get('duration', 0))
        }
    except Exception:
        return {}


def add_asset(
    file_path: str,
    asset_id: str,
    tags: list,
    category: str,
    asset_type: str = 'broll',
    description: str = '',
    cloudinary_url: Optional[str] = None,
    manifest: Optional[dict] = None
) -> dict:
    """Add new asset to manifest."""
    if manifest is None:
        manifest = load_manifest()

    # Get file info
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine relative path
    assets_dir = get_manifest_path().parent
    try:
        rel_path = file_path.relative_to(assets_dir)
    except ValueError:
        # File not in assets dir, use filename
        rel_path = f"{asset_type}/{category}/{file_path.name}"

    # Get video info if applicable
    video_info = {}
    if file_path.suffix.lower() in ['.mp4', '.mov', '.webm', '.avi']:
        video_info = get_video_info(str(file_path))

    # Build asset entry
    asset = {
        'id': asset_id,
        'path': str(rel_path),
        'type': asset_type,
        'category': category,
        'duration': video_info.get('duration'),
        'resolution': f"{video_info.get('width')}x{video_info.get('height')}" if video_info.get('width') else None,
        'tags': tags,
        'cloudinary_url': cloudinary_url,
        'description': description
    }

    # Check for duplicate ID
    existing_ids = [a['id'] for a in manifest.get('assets', [])]
    if asset_id in existing_ids:
        # Update existing
        for i, a in enumerate(manifest['assets']):
            if a['id'] == asset_id:
                manifest['assets'][i] = asset
                break
    else:
        manifest['assets'].append(asset)

    save_manifest(manifest)
    return asset


def remove_asset(asset_id: str, manifest: Optional[dict] = None) -> bool:
    """Remove asset from manifest."""
    if manifest is None:
        manifest = load_manifest()

    original_count = len(manifest.get('assets', []))
    manifest['assets'] = [a for a in manifest.get('assets', []) if a.get('id') != asset_id]

    if len(manifest['assets']) < original_count:
        save_manifest(manifest)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description='Manage B-roll and graphics asset library'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search assets by keywords')
    search_parser.add_argument('keywords', nargs='+', help='Keywords to search for')
    search_parser.add_argument('--type', choices=['broll', 'graphic', 'audio'], help='Filter by type')
    search_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # List command
    list_parser = subparsers.add_parser('list', help='List assets')
    list_parser.add_argument('--type', choices=['broll', 'graphic', 'audio'], help='Filter by type')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Info command
    info_parser = subparsers.add_parser('info', help='Get asset details')
    info_parser.add_argument('asset_id', help='Asset ID')
    info_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add new asset')
    add_parser.add_argument('file_path', help='Path to asset file')
    add_parser.add_argument('--id', required=True, help='Unique asset ID')
    add_parser.add_argument('--tags', required=True, help='Comma-separated tags')
    add_parser.add_argument('--category', required=True, help='Asset category')
    add_parser.add_argument('--type', default='broll', choices=['broll', 'graphic', 'audio'], help='Asset type')
    add_parser.add_argument('--description', default='', help='Asset description')
    add_parser.add_argument('--cloudinary-url', help='Cloudinary URL if uploaded')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove asset from manifest')
    remove_parser.add_argument('asset_id', help='Asset ID to remove')

    args = parser.parse_args()

    if args.command == 'search':
        results = search_assets(args.keywords, args.type)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"No assets found matching: {' '.join(args.keywords)}")
            else:
                print(f"Found {len(results)} assets:\n")
                for asset in results[:10]:
                    print(f"  {asset['id']} ({asset['type']}/{asset['category']})")
                    print(f"    Tags: {', '.join(asset.get('matched_tags', []))}")
                    print(f"    Score: {asset['match_score']}")
                    if asset.get('duration'):
                        print(f"    Duration: {asset['duration']:.1f}s")
                    print()

    elif args.command == 'list':
        results = list_assets(args.type, args.category)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No assets found")
            else:
                print(f"Assets ({len(results)}):\n")
                for asset in results:
                    print(f"  {asset['id']}")
                    print(f"    Type: {asset['type']}/{asset.get('category', 'unknown')}")
                    print(f"    Tags: {', '.join(asset.get('tags', [])[:5])}")
                    print()

    elif args.command == 'info':
        asset = get_asset_info(args.asset_id)

        if not asset:
            print(f"Asset not found: {args.asset_id}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(asset, indent=2))
        else:
            print(f"Asset: {asset['id']}")
            print(f"  Path: {asset.get('path')}")
            print(f"  Type: {asset.get('type')}/{asset.get('category')}")
            print(f"  Tags: {', '.join(asset.get('tags', []))}")
            if asset.get('duration'):
                print(f"  Duration: {asset['duration']:.1f}s")
            if asset.get('resolution'):
                print(f"  Resolution: {asset['resolution']}")
            if asset.get('cloudinary_url'):
                print(f"  Cloudinary: {asset['cloudinary_url']}")
            if asset.get('description'):
                print(f"  Description: {asset['description']}")

    elif args.command == 'add':
        tags = [t.strip() for t in args.tags.split(',')]

        try:
            asset = add_asset(
                file_path=args.file_path,
                asset_id=args.id,
                tags=tags,
                category=args.category,
                asset_type=args.type,
                description=args.description,
                cloudinary_url=args.cloudinary_url
            )
            print(f"Added asset: {asset['id']}")
            print(f"  Path: {asset['path']}")
            print(f"  Tags: {', '.join(asset['tags'])}")
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'remove':
        if remove_asset(args.asset_id):
            print(f"Removed asset: {args.asset_id}")
        else:
            print(f"Asset not found: {args.asset_id}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
