#!/usr/bin/env python3
"""
CEO Content Engine - Main Entry Point

Repurposes video transcripts into multi-platform content.

Usage:
    python repurpose.py <folder_path>           # Full pipeline
    python repurpose.py --list                  # List available folders
    python repurpose.py --status <folder>       # Check manifest status
    python repurpose.py --extract <folder>      # Extract insights only
    python repurpose.py --generate <folder>     # Generate content only (requires insights)
    python repurpose.py --test                  # Run with test transcript

With Feedback:
    python repurpose.py <folder> -f "Focus on practical implementation"
    python repurpose.py <folder> --feedback "Emphasize ROI, make LinkedIn more technical"
    python repurpose.py --extract <folder> -f "Prioritize contrarian insights"
    python repurpose.py --generate <folder> -f "More provocative tone for Twitter"

Feedback affects both extraction (what insights to prioritize) and generation
(how to write the content). Feedback is stored in the manifest for reference.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from manifest import (
    Manifest,
    STATUS_STARTED,
    STATUS_EXTRACTING_INSIGHTS,
    STATUS_GENERATING_CONTENT,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from extraction import extract_from_folder, count_words, load_transcript
from utils.tov import get_tov_profile, get_available_platforms
from .knowledge_base import is_knowledge_base_available, enrich_insight
from utils.feedback import process_feedback
from utils.guests import load_guests, format_guest_summary, find_guest_photos, create_guests_template


def run_full_pipeline(
    folder_path: str,
    content_types: list[str] = None,
    use_knowledge_base: bool = True,
    verbose: bool = True,
    user_feedback: str = None,
    mode: str = "solo",
    guests: list[dict] = None,
) -> bool:
    """
    Run the full repurposing pipeline.

    Args:
        folder_path: Path to folder containing transcript.md
        content_types: List of content types to generate (None = all)
        use_knowledge_base: Whether to use the knowledge base agent enrichment
        verbose: Print progress messages
        user_feedback: Optional user feedback/direction for extraction and generation
        mode: Content mode - "solo" or "podcast"
        guests: List of guest dictionaries (for podcast mode)

    Returns:
        True if successful
    """
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder not found: {folder}")
        return False

    transcript_path = folder / "transcript.md"
    if not transcript_path.exists():
        print(f"Error: transcript.md not found in {folder}")
        return False

    # Process feedback if provided
    processed_feedback = "NO_FEEDBACK"
    if user_feedback:
        if verbose:
            print("Processing user feedback...")
        processed_feedback = process_feedback(user_feedback, verbose)
        if processed_feedback != "NO_FEEDBACK" and verbose:
            print(f"Feedback applied: {processed_feedback[:100]}...")

    if verbose:
        print("=" * 60)
        print("CEO Content Engine - Ruby Native Pipeline")
        print("=" * 60)
        print(f"Folder: {folder}")
        print(f"Mode: {mode}")
        print(f"the knowledge base agent: {'enabled' if use_knowledge_base and is_knowledge_base_available() else 'disabled'}")
        if processed_feedback != "NO_FEEDBACK":
            print(f"Feedback: Applied")
        if mode == "podcast" and guests:
            print(f"Guests: {len(guests)} loaded")
            for g in guests:
                print(f"  - {g['name']}" + (f" ({g['twitter']})" if g.get('twitter') else ""))
        print("-" * 60)

    # Load transcript and count words
    transcript = load_transcript(str(folder))
    word_count = count_words(transcript) if transcript else 0

    # Create or load manifest
    manifest = Manifest.load_or_create(str(folder), word_count)

    # Store feedback in manifest for reference
    if processed_feedback != "NO_FEEDBACK":
        manifest.set_user_feedback(processed_feedback)

    # Check if already completed
    if manifest.is_completed():
        if verbose:
            print("Content already generated. Use --force to regenerate.")
        manifest.print_summary()
        return True

    try:
        # Stage 1: Extract insights
        if verbose:
            print("\n[Stage 1] Extracting insights...")

        manifest.update_status(STATUS_EXTRACTING_INSIGHTS, "Starting extraction")

        extraction_result = extract_from_folder(str(folder), verbose, processed_feedback)

        if not extraction_result:
            manifest.update_status(STATUS_FAILED, error="Extraction failed")
            print("Error: Insight extraction failed")
            return False

        # Add insights to manifest
        insights = extraction_result.get("insights", [])
        if not insights:
            manifest.update_status(STATUS_FAILED, error="No insights extracted")
            print("Error: No insights extracted")
            return False

        manifest.add_insights_batch(insights)

        if verbose:
            print(f"Extracted {len(insights)} insights")

        # Stage 2: Optional the knowledge base agent enrichment
        if use_knowledge_base and is_knowledge_base_available():
            if verbose:
                print("\n[Stage 2] Enriching with the knowledge base agent...")

            for i, insight in enumerate(manifest.get_all_insights()):
                enriched = enrich_insight(insight)
                # Update in place (already modified)
            manifest.set_knowledge_base_used(True)
        else:
            manifest.set_knowledge_base_used(False)

        # Stage 3: Generate content
        if verbose:
            print("\n[Stage 3] Generating content...")

        manifest.update_status(STATUS_GENERATING_CONTENT, "Starting content generation")

        # Load TOV profiles
        tov_profiles = {}
        platforms_needed = ["linkedin", "twitter", "newsletter", "community_post", "text_post", "carousel"]

        for platform in platforms_needed:
            profile = get_tov_profile(platform)
            if profile:
                tov_profiles[platform] = profile
                manifest.add_tov_profile_used(platform, auto_save=False)

        # Import generators here to avoid circular imports
        from generators import generate_all_for_insight, get_available_generators

        if content_types is None:
            content_types = get_available_generators()

        output_dir = manifest.get_generated_content_path()

        # Generate content for each insight
        for insight in manifest.get_all_insights():
            insight_id = insight["id"]

            if verbose:
                print(f"\nProcessing insight {insight_id}...")

            results = generate_all_for_insight(
                insight=insight,
                tov_profiles=tov_profiles,
                output_dir=output_dir,
                insight_number=insight_id,
                content_types=content_types,
                user_feedback=processed_feedback,
            )

            # Update manifest with generated folders/files
            for content_type, file_path in results.items():
                if file_path:
                    # Record the subfolder name (parent of the content file)
                    content_path = Path(file_path)
                    subfolder_name = content_path.parent.name
                    # If the parent is the output_dir itself, use the filename
                    if content_path.parent == output_dir:
                        subfolder_name = content_path.name
                    manifest.add_generated_content(insight_id, content_type, subfolder_name, auto_save=False)

        # Stage 4: Complete
        manifest.update_status(STATUS_COMPLETED, "Pipeline complete")

        if verbose:
            print("\n" + "=" * 60)
            print("PIPELINE COMPLETE")
            manifest.print_summary()

        return True

    except Exception as e:
        manifest.update_status(STATUS_FAILED, error=str(e))
        print(f"Error: Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_only(folder_path: str, verbose: bool = True, user_feedback: str = None) -> bool:
    """Run extraction stage only."""
    folder = Path(folder_path)

    if not (folder / "transcript.md").exists():
        print(f"Error: transcript.md not found in {folder}")
        return False

    # Process feedback if provided
    processed_feedback = "NO_FEEDBACK"
    if user_feedback:
        if verbose:
            print("Processing user feedback for extraction...")
        processed_feedback = process_feedback(user_feedback, verbose)
        if processed_feedback != "NO_FEEDBACK" and verbose:
            print(f"Feedback applied: {processed_feedback[:100]}...")

    transcript = load_transcript(str(folder))
    word_count = count_words(transcript) if transcript else 0

    manifest = Manifest.load_or_create(str(folder), word_count)
    manifest.update_status(STATUS_EXTRACTING_INSIGHTS)

    # Store feedback in manifest
    if processed_feedback != "NO_FEEDBACK":
        manifest.set_user_feedback(processed_feedback)

    result = extract_from_folder(str(folder), verbose, processed_feedback)

    if result and "insights" in result:
        manifest.add_insights_batch(result["insights"])
        manifest.save()
        print(f"Extracted {len(result['insights'])} insights")
        return True

    manifest.update_status(STATUS_FAILED, error="Extraction failed")
    return False


def generate_only(folder_path: str, content_types: list[str] = None, verbose: bool = True, user_feedback: str = None) -> bool:
    """Run generation stage only (requires existing insights)."""
    folder = Path(folder_path)

    manifest = Manifest.load(str(folder))
    if not manifest:
        print("Error: No manifest found. Run extraction first.")
        return False

    insights = manifest.get_all_insights()
    if not insights:
        print("Error: No insights in manifest. Run extraction first.")
        return False

    # Process feedback if provided
    processed_feedback = "NO_FEEDBACK"
    if user_feedback:
        if verbose:
            print("Processing user feedback for generation...")
        processed_feedback = process_feedback(user_feedback, verbose)
        if processed_feedback != "NO_FEEDBACK" and verbose:
            print(f"Feedback applied: {processed_feedback[:100]}...")
    else:
        # Check if feedback was stored in manifest from extraction
        stored_feedback = manifest.get_user_feedback()
        if stored_feedback and stored_feedback != "NO_FEEDBACK":
            processed_feedback = stored_feedback
            if verbose:
                print(f"Using feedback from extraction: {processed_feedback[:100]}...")

    manifest.update_status(STATUS_GENERATING_CONTENT)

    # Update feedback in manifest if new feedback provided
    if user_feedback and processed_feedback != "NO_FEEDBACK":
        manifest.set_user_feedback(processed_feedback)

    # Load TOV profiles
    tov_profiles = {}
    for platform in ["linkedin", "twitter", "newsletter", "community_post", "text_post", "carousel"]:
        profile = get_tov_profile(platform)
        if profile:
            tov_profiles[platform] = profile

    from generators import generate_all_for_insight, get_available_generators

    if content_types is None:
        content_types = get_available_generators()

    output_dir = manifest.get_generated_content_path()

    for insight in insights:
        insight_id = insight["id"]
        if verbose:
            print(f"Generating for insight {insight_id}...")

        results = generate_all_for_insight(
            insight=insight,
            tov_profiles=tov_profiles,
            output_dir=output_dir,
            insight_number=insight_id,
            content_types=content_types,
            user_feedback=processed_feedback,
            mode=mode,
            guests=guests,
        )

        for content_type, file_path in results.items():
            if file_path:
                # Record the subfolder name (parent of the content file)
                content_path = Path(file_path)
                subfolder_name = content_path.parent.name
                if content_path.parent == output_dir:
                    subfolder_name = content_path.name
                manifest.add_generated_content(insight_id, content_type, subfolder_name, auto_save=False)

    manifest.update_status(STATUS_COMPLETED)
    manifest.save()

    if verbose:
        manifest.print_summary()

    return True


def show_status(folder_path: str) -> None:
    """Show manifest status for a folder."""
    manifest = Manifest.load(folder_path)
    if manifest:
        manifest.print_summary()
    else:
        print(f"No manifest found in {folder_path}")


def list_folders() -> None:
    """List available content folders."""
    # This would ideally use Google Drive API
    # For now, show test folder
    print("Available folders:")
    print("  (Use Google Drive API or specify full path)")
    print("")
    print("Test folder:")
    test_folder = Config.get_project_root() / "resources" / "temp" / "Test"
    if test_folder.exists():
        print(f"  {test_folder}")
    else:
        print("  No test folder found")


def main():
    parser = argparse.ArgumentParser(
        description="CEO Content Engine - Repurpose video transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python repurpose.py /path/to/folder           # Full pipeline
  python repurpose.py --test                    # Test with sample
  python repurpose.py --extract /path/to/folder # Extract only
  python repurpose.py --status /path/to/folder  # Check status
        """
    )

    parser.add_argument("folder", nargs="?", help="Folder path containing transcript.md")
    parser.add_argument("--test", action="store_true", help="Run with test transcript")
    parser.add_argument("--list", action="store_true", help="List available folders")
    parser.add_argument("--status", metavar="FOLDER", help="Show manifest status")
    parser.add_argument("--extract", metavar="FOLDER", help="Extract insights only")
    parser.add_argument("--generate", metavar="FOLDER", help="Generate content only")
    parser.add_argument("--types", help="Content types to generate (comma-separated)")
    parser.add_argument("--mode", choices=["solo", "podcast"], default="solo",
                       help="Content mode: solo (default) or podcast")
    parser.add_argument("--no-knowledge_base", action="store_true", help="Disable the knowledge base agent enrichment")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip interactive confirmations (for automation)")
    parser.add_argument("--config", action="store_true", help="Show configuration")
    parser.add_argument(
        "--feedback", "-f",
        help="User feedback/direction for content extraction and generation. "
             "Examples: 'Focus on practical implementation', 'Emphasize ROI metrics', "
             "'Make LinkedIn more technical'"
    )

    args = parser.parse_args()

    # Handle content types
    content_types = None
    if args.types:
        content_types = [t.strip() for t in args.types.split(",")]

    verbose = not args.quiet

    # Handle commands
    if args.config:
        Config.print_config_summary()
        return 0

    if args.list:
        list_folders()
        return 0

    if args.status:
        show_status(args.status)
        return 0

    if args.extract:
        success = extract_only(args.extract, verbose, user_feedback=args.feedback)
        return 0 if success else 1

    if args.generate:
        success = generate_only(args.generate, content_types, verbose, user_feedback=args.feedback)
        return 0 if success else 1

    if args.test:
        test_folder = str(Config.get_project_root() / "resources" / "temp" / "Test")
        success = run_full_pipeline(
            test_folder,
            content_types=content_types,
            use_knowledge_base=not args.no_knowledge_base,
            verbose=verbose,
            user_feedback=args.feedback,
        )
        return 0 if success else 1

    if args.folder:
        guests = None

        # Handle podcast mode
        if args.mode == "podcast":
            folder = Path(args.folder)
            guests_file = folder / "guests.md"

            if not guests_file.exists():
                print(f"Error: Podcast mode requires guests.md in {folder}")
                print(f"\nCreate guests.md with guest information:")
                print(f"  # Podcast Guests")
                print(f"  ")
                print(f"  ## Guest Name")
                print(f"  - slug: guest_name")
                print(f"  - twitter: @handle")
                print(f"  - linkedin: linkedin.com/in/username")
                print(f"  - company: Company Name")
                print(f"  - photos: guest_photos/*.jpg")
                return 1

            # Load guests
            guests = load_guests(args.folder)
            if not guests:
                print(f"Error: No guests found in guests.md")
                return 1

            # Display for approval
            print("\n" + "=" * 60)
            print("[APPROVAL GATE] Verify Guest Information")
            print("=" * 60)
            print(format_guest_summary(guests, args.folder))

            if args.yes:
                print("Guest information auto-confirmed (--yes flag).\n")
            else:
                print("Is this information correct?")
                print("  1. Yes, proceed")
                print("  2. Edit guests.md first")
                print("  3. Abort")
                print()

                try:
                    choice = input("Enter choice [1/2/3]: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\nAborted.")
                    return 1

                if choice == "2":
                    print(f"\nEdit {guests_file} and run again.")
                    return 1
                elif choice != "1":
                    print("\nAborted.")
                    return 1

                print("\nGuest information confirmed. Proceeding...\n")

        success = run_full_pipeline(
            args.folder,
            content_types=content_types,
            use_knowledge_base=not args.no_knowledge_base,
            verbose=verbose,
            user_feedback=args.feedback,
            mode=args.mode,
            guests=guests,
        )
        return 0 if success else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
