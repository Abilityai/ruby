"""
Manifest module for CEO Content Engine repurpose functionality.

Handles file-based job tracking using _manifest.json files,
replacing the Supabase database approach from N8N.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


# Status constants
STATUS_STARTED = "started"
STATUS_EXTRACTING_INSIGHTS = "extracting_insights"
STATUS_GENERATING_CONTENT = "generating_content"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

VALID_STATUSES = [
    STATUS_STARTED,
    STATUS_EXTRACTING_INSIGHTS,
    STATUS_GENERATING_CONTENT,
    STATUS_COMPLETED,
    STATUS_FAILED,
]

# Content types
CONTENT_TYPES = [
    "linkedin_post",
    "twitter_thread",
    "newsletter",
    "community_post",
    "text_post",
    "linkedin_carousel",
    "blog_post",
]


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _now_folder_timestamp() -> str:
    """Get current timestamp for folder naming (YYYY-MM-DD_HH:MM:SS)."""
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


@dataclass
class InsightScores:
    """Scores for an extracted insight."""
    impact: int = 0
    clarity: int = 0
    uniqueness: int = 0
    actionability: int = 0
    overall_score: float = 0.0


@dataclass
class GeneratedContent:
    """Tracks generated content files for an insight."""
    linkedin_post: Optional[str] = None
    twitter_thread: Optional[str] = None
    newsletter: Optional[str] = None
    community_post: Optional[str] = None
    text_post: Optional[str] = None
    linkedin_carousel: Optional[str] = None
    blog_post: Optional[str] = None


@dataclass
class Insight:
    """An extracted insight from the transcript."""
    id: int
    core_insight: str
    scores: InsightScores = field(default_factory=InsightScores)
    quotable_moments: list[str] = field(default_factory=list)
    story_elements: str = ""
    thought_leadership_angle: str = ""
    supporting_context: str = ""
    potential_formats: list[str] = field(default_factory=list)
    generated_content: GeneratedContent = field(default_factory=GeneratedContent)


@dataclass
class StatusEntry:
    """A status history entry."""
    status: str
    timestamp: str
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Statistics:
    """Statistics about generated content."""
    total_insights: int = 0
    total_content_pieces: int = 0
    by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class Metadata:
    """Manifest metadata."""
    generator: str = "ruby-repurpose-skill"
    version: str = "2.0"
    knowledge_base_used: bool = False
    tov_profiles_used: list[str] = field(default_factory=list)


@dataclass
class Source:
    """Source content information."""
    transcript_path: str = "transcript.md"
    processed_at: Optional[str] = None
    word_count: int = 0


class Manifest:
    """
    Manages the _manifest.json file for tracking repurpose job state.

    Replaces the Supabase database approach with a file-based solution.
    """

    MANIFEST_VERSION = "2.0"  # Production release
    MANIFEST_FILENAME = "_manifest.json"
    FOLDER_PREFIX = "Generated Content"

    def __init__(self, folder_path: str, output_folder_name: str = None):
        """
        Initialize manifest for a folder.

        Args:
            folder_path: Path to the folder containing transcript.md
            output_folder_name: Optional specific output folder name (for loading existing)
        """
        self.folder_path = Path(folder_path)

        if output_folder_name:
            # Use provided folder name (for loading existing manifest)
            self.generated_content_path = self.folder_path / output_folder_name
        else:
            # Will be set properly during create() with timestamp
            self.generated_content_path = None

        if self.generated_content_path:
            self.manifest_path = self.generated_content_path / self.MANIFEST_FILENAME
        else:
            self.manifest_path = None

        # Initialize data structure
        self._data = {
            "version": self.MANIFEST_VERSION,
            "source": {
                "transcript_path": "transcript.md",
                "processed_at": None,
                "word_count": 0,
            },
            "insights": [],
            "status": {
                "current": STATUS_STARTED,
                "history": [],
            },
            "statistics": {
                "total_insights": 0,
                "total_content_pieces": 0,
                "by_type": {},
            },
            "metadata": {
                "generator": "ruby-repurpose-skill",
                "version": "2.0",
                "knowledge_base_used": False,
                "tov_profiles_used": [],
            },
        }

    @classmethod
    def create(cls, folder_path: str, word_count: int = 0) -> "Manifest":
        """
        Create a new manifest for a folder.

        Args:
            folder_path: Path to the folder
            word_count: Word count of the transcript

        Returns:
            New Manifest instance
        """
        # Create timestamped folder name
        timestamp = _now_folder_timestamp()
        output_folder_name = f"{cls.FOLDER_PREFIX}_{timestamp}"

        manifest = cls(folder_path, output_folder_name)

        # Ensure Generated Content folder exists
        manifest.generated_content_path.mkdir(parents=True, exist_ok=True)

        # Store the folder name in data for later retrieval
        manifest._data["output_folder"] = output_folder_name

        # Initialize with starting values
        manifest._data["source"]["processed_at"] = _now_iso()
        manifest._data["source"]["word_count"] = word_count
        manifest._add_status_entry(STATUS_STARTED)

        # Save initial manifest
        manifest.save()

        return manifest

    @classmethod
    def load(cls, folder_path: str) -> Optional["Manifest"]:
        """
        Load an existing manifest from a folder.

        Searches for the most recent Generated Content_* folder with a manifest.

        Args:
            folder_path: Path to the folder

        Returns:
            Manifest instance or None if not found
        """
        folder = Path(folder_path)

        # Find all Generated Content_* folders
        content_folders = sorted(
            folder.glob(f"{cls.FOLDER_PREFIX}_*"),
            reverse=True  # Most recent first (timestamp sort)
        )

        # Also check for legacy "Generated Content" folder (no timestamp)
        legacy_folder = folder / "Generated Content"
        if legacy_folder.exists() and legacy_folder.is_dir():
            content_folders.append(legacy_folder)

        # Find the first folder with a manifest
        for content_folder in content_folders:
            manifest_file = content_folder / cls.MANIFEST_FILENAME
            if manifest_file.exists():
                try:
                    manifest = cls(folder_path, content_folder.name)
                    with open(manifest_file, "r") as f:
                        manifest._data = json.load(f)
                    return manifest
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading manifest from {content_folder}: {e}")
                    continue

        return None

    @classmethod
    def load_or_create(cls, folder_path: str, word_count: int = 0) -> "Manifest":
        """
        Load existing manifest or create new one.

        Args:
            folder_path: Path to the folder
            word_count: Word count for new manifest

        Returns:
            Manifest instance
        """
        existing = cls.load(folder_path)
        if existing:
            return existing
        return cls.create(folder_path, word_count)

    def save(self) -> None:
        """Save manifest to file."""
        # Ensure directory exists
        self.generated_content_path.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _add_status_entry(
        self,
        status: str,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Add a status entry to history."""
        entry = {
            "status": status,
            "timestamp": _now_iso(),
        }
        if message:
            entry["message"] = message
        if error:
            entry["error"] = error

        self._data["status"]["history"].append(entry)
        self._data["status"]["current"] = status

    def update_status(
        self,
        status: str,
        message: Optional[str] = None,
        error: Optional[str] = None,
        auto_save: bool = True
    ) -> None:
        """
        Update the current status.

        Args:
            status: New status (one of VALID_STATUSES)
            message: Optional message
            error: Optional error message (for failed status)
            auto_save: Whether to auto-save after update
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

        self._add_status_entry(status, message, error)

        if auto_save:
            self.save()

    def get_status(self) -> str:
        """Get current status."""
        return self._data["status"]["current"]

    def is_completed(self) -> bool:
        """Check if processing is completed."""
        return self.get_status() == STATUS_COMPLETED

    def is_failed(self) -> bool:
        """Check if processing failed."""
        return self.get_status() == STATUS_FAILED

    def add_insight(self, insight_data: dict, auto_save: bool = True) -> int:
        """
        Add an extracted insight.

        Args:
            insight_data: Insight dictionary with required fields
            auto_save: Whether to auto-save after adding

        Returns:
            The insight ID (1-based index)
        """
        insight_id = len(self._data["insights"]) + 1

        # Normalize insight data
        insight = {
            "id": insight_id,
            "core_insight": insight_data.get("core_insight", ""),
            "scores": insight_data.get("scores", {
                "impact": 0,
                "clarity": 0,
                "uniqueness": 0,
                "actionability": 0,
                "overall_score": 0.0,
            }),
            "quotable_moments": insight_data.get("quotable_moments", []),
            "story_elements": insight_data.get("story_elements", ""),
            "thought_leadership_angle": insight_data.get("thought_leadership_angle", ""),
            "supporting_context": insight_data.get("supporting_context", ""),
            "potential_formats": insight_data.get("potential_formats", []),
            "generated_content": {
                "linkedin_post": None,
                "twitter_thread": None,
                "newsletter": None,
                "community_post": None,
                "text_post": None,
                "linkedin_carousel": None,
                "blog_post": None,
            },
        }

        self._data["insights"].append(insight)
        self._data["statistics"]["total_insights"] = len(self._data["insights"])

        if auto_save:
            self.save()

        return insight_id

    def add_insights_batch(self, insights: list[dict], auto_save: bool = True) -> list[int]:
        """
        Add multiple insights at once.

        Args:
            insights: List of insight dictionaries
            auto_save: Whether to auto-save after adding

        Returns:
            List of insight IDs
        """
        ids = []
        for insight_data in insights:
            insight_id = self.add_insight(insight_data, auto_save=False)
            ids.append(insight_id)

        if auto_save:
            self.save()

        return ids

    def add_generated_content(
        self,
        insight_id: int,
        content_type: str,
        filename: str,
        auto_save: bool = True
    ) -> None:
        """
        Record generated content for an insight.

        Args:
            insight_id: ID of the insight (1-based)
            content_type: Type of content (e.g., "linkedin_post")
            filename: Filename of the generated content
            auto_save: Whether to auto-save after update
        """
        if content_type not in CONTENT_TYPES:
            raise ValueError(f"Invalid content type: {content_type}")

        # Find insight by ID
        for insight in self._data["insights"]:
            if insight["id"] == insight_id:
                insight["generated_content"][content_type] = filename

                # Update statistics
                self._update_statistics()

                if auto_save:
                    self.save()
                return

        raise ValueError(f"Insight with ID {insight_id} not found")

    def _update_statistics(self) -> None:
        """Recalculate statistics from current data."""
        by_type = {ct: 0 for ct in CONTENT_TYPES}
        total_pieces = 0

        for insight in self._data["insights"]:
            for content_type in CONTENT_TYPES:
                if insight.get("generated_content", {}).get(content_type):
                    by_type[content_type] += 1
                    total_pieces += 1

        self._data["statistics"]["by_type"] = by_type
        self._data["statistics"]["total_content_pieces"] = total_pieces

    def get_insight(self, insight_id: int) -> Optional[dict]:
        """Get an insight by ID."""
        for insight in self._data["insights"]:
            if insight["id"] == insight_id:
                return insight
        return None

    def get_all_insights(self) -> list[dict]:
        """Get all insights."""
        return self._data["insights"]

    def get_statistics(self) -> dict:
        """Get current statistics."""
        return self._data["statistics"]

    def set_knowledge_base_used(self, used: bool, auto_save: bool = True) -> None:
        """Mark whether the knowledge base agent was used."""
        self._data["metadata"]["knowledge_base_used"] = used
        if auto_save:
            self.save()

    def add_tov_profile_used(self, profile: str, auto_save: bool = True) -> None:
        """Record a TOV profile that was used."""
        if profile not in self._data["metadata"]["tov_profiles_used"]:
            self._data["metadata"]["tov_profiles_used"].append(profile)
        if auto_save:
            self.save()

    def set_user_feedback(self, feedback: str, auto_save: bool = True) -> None:
        """
        Store user feedback for reference.

        Args:
            feedback: Processed user feedback string
            auto_save: Whether to auto-save after update
        """
        self._data["metadata"]["user_feedback"] = feedback
        if auto_save:
            self.save()

    def get_user_feedback(self) -> Optional[str]:
        """
        Get stored user feedback.

        Returns:
            Feedback string or None if not set
        """
        return self._data.get("metadata", {}).get("user_feedback")

    def get_generated_content_path(self) -> Path:
        """Get the Generated Content folder path."""
        return self.generated_content_path

    def to_dict(self) -> dict:
        """Convert manifest to dictionary."""
        return self._data.copy()

    def print_summary(self) -> None:
        """Print a human-readable summary of the manifest."""
        print("=" * 50)
        print("Manifest Summary")
        print("=" * 50)
        print(f"Folder: {self.folder_path}")
        print(f"Status: {self.get_status()}")
        print(f"Insights: {self._data['statistics']['total_insights']}")
        print(f"Content Pieces: {self._data['statistics']['total_content_pieces']}")
        print("-" * 50)
        print("Content by Type:")
        for ct, count in self._data["statistics"].get("by_type", {}).items():
            if count > 0:
                print(f"  {ct}: {count}")
        print("-" * 50)
        print(f"the knowledge base agent Used: {self._data['metadata']['knowledge_base_used']}")
        print(f"TOV Profiles: {', '.join(self._data['metadata']['tov_profiles_used']) or 'None'}")
        print("=" * 50)


def read_manifest(folder_path: str) -> Optional[dict]:
    """
    Read manifest from a folder.

    Convenience function for quick access.

    Args:
        folder_path: Path to the folder

    Returns:
        Manifest data as dict or None
    """
    manifest = Manifest.load(folder_path)
    return manifest.to_dict() if manifest else None


def create_manifest(folder_path: str, word_count: int = 0) -> dict:
    """
    Create a new manifest.

    Convenience function for quick creation.

    Args:
        folder_path: Path to the folder
        word_count: Word count of transcript

    Returns:
        Created manifest data as dict
    """
    manifest = Manifest.create(folder_path, word_count)
    return manifest.to_dict()


if __name__ == "__main__":
    # Test the manifest module
    import tempfile
    import shutil

    print("Testing Manifest Module")
    print("=" * 50)

    # Create a temporary test folder
    test_folder = tempfile.mkdtemp(prefix="manifest_test_")
    print(f"Test folder: {test_folder}")

    try:
        # Create manifest
        manifest = Manifest.create(test_folder, word_count=4250)
        print("Created new manifest")

        # Update status
        manifest.update_status(STATUS_EXTRACTING_INSIGHTS, "Starting extraction...")
        print(f"Status updated to: {manifest.get_status()}")

        # Add insights
        insight_data = {
            "core_insight": "Context windows are the new bottleneck for AI agents",
            "scores": {
                "impact": 9,
                "clarity": 8,
                "uniqueness": 9,
                "actionability": 7,
                "overall_score": 8.25,
            },
            "quotable_moments": ["Quote 1", "Quote 2"],
            "thought_leadership_angle": "Contrarian view on context management",
            "supporting_context": "Technical details about token limits",
            "potential_formats": ["linkedin_post", "twitter_thread"],
        }

        insight_id = manifest.add_insight(insight_data)
        print(f"Added insight with ID: {insight_id}")

        # Add generated content
        manifest.update_status(STATUS_GENERATING_CONTENT)
        manifest.add_generated_content(insight_id, "linkedin_post", "linkedin_post_001.md")
        manifest.add_generated_content(insight_id, "twitter_thread", "twitter_thread_001.md")
        print("Added generated content references")

        # Complete
        manifest.update_status(STATUS_COMPLETED)
        manifest.set_knowledge_base_used(False)
        manifest.add_tov_profile_used("linkedin")
        manifest.add_tov_profile_used("twitter")

        # Print summary
        manifest.print_summary()

        # Verify file was created
        manifest_file = Path(test_folder) / "Generated Content" / "_manifest.json"
        print(f"\nManifest file exists: {manifest_file.exists()}")

        # Test loading
        loaded = Manifest.load(test_folder)
        print(f"Loaded manifest status: {loaded.get_status()}")

        print("\nAll tests passed!")

    finally:
        # Cleanup
        shutil.rmtree(test_folder)
        print(f"Cleaned up test folder")
