"""
Configuration module for CEO Content Engine repurpose functionality.

Handles environment detection, path resolution, TOV file mapping,
and the knowledge base agent integration settings.
"""

import os
from pathlib import Path
from typing import Optional


def _load_dotenv_manual():
    """Load .env file manually without python-dotenv dependency."""
    # Find project root
    current = Path(__file__).resolve()
    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse KEY=VALUE
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value and value[0] in ('"', "'") and value[-1] == value[0]:
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key and key not in os.environ:
                            os.environ[key] = value
            return
        current = current.parent


# Load environment variables from .env file
_load_dotenv_manual()


class Config:
    """Central configuration class for the repurpose module."""

    # TOV (Tone of Voice) file IDs from Google Drive
    TOV_FILE_IDS = {
        "twitter": "YOUR_TWITTER_TOV_ID",
        "linkedin": "YOUR_LINKEDIN_TOV_ID",
        "heygen": "YOUR_HEYGEN_TOV_ID",
        "text_post": "YOUR_TEXT_POST_TOV_ID",
        "newsletter": "YOUR_NEWSLETTER_TOV_ID",
        "community_post": "YOUR_COMMUNITY_TOV_ID",
        "carousel": "YOUR_CAROUSEL_TOV_ID",
        "long_form": "YOUR_LONGFORM_TOV_ID",
    }

    # Google Drive folder IDs
    GDRIVE_FOLDERS = {
        "root": "YOUR_DRIVE_ROOT_ID",
        "content": "YOUR_CONTENT_FOLDER_ID",
        "prompts": "YOUR_PROMPTS_FOLDER_ID",
        "generated_shorts": "YOUR_SHORTS_FOLDER_ID",
        "reference_photos": "YOUR_PHOTOS_FOLDER_ID",  # Reference Photos
    }

    # APITemplate.io template IDs
    APITEMPLATE_TEMPLATES = {
        "carousel": "d1677b23e271267e",
        "carousel_alt": "c8877b23e275116a",
        "framer_cover": "6d577b235f5c06ca",
    }

    # Timeout configuration (in seconds)
    TIMEOUTS = {
        "pipeline_total": 1200,  # 20 minutes for full pipeline
        "midjourney_image": 300,  # 5 minutes for image generation
        "apitemplate_pdf": 120,  # 2 minutes for PDF generation
        "gemini_call": 60,  # 1 minute for Gemini API calls
    }

    # Retry configuration
    RETRY_CONFIG = {
        "max_retries": 3,
        "cooldown_seconds": 15,
    }

    # Gemini model configuration
    GEMINI_MODELS = {
        "primary": "gemini-3-pro-preview",
        "fallback": "gemini-2.5-pro",
        "image": "gemini-3-pro-image-preview",
    }

    # Content type configurations
    CONTENT_TYPES = [
        "linkedin_post",
        "twitter_thread",
        "newsletter",
        "community_post",
        "text_post",
        "linkedin_carousel",
        "framer_cms",
    ]

    @staticmethod
    def knowledge_base_path() -> str:
        """Get the path to the knowledge base agent agent."""
        return os.getenv("KNOWLEDGE_BASE_AGENT_PATH", "${KNOWLEDGE_BASE_AGENT_PATH}")

    @staticmethod
    def get_output_dir(folder_path: str) -> str:
        """Get the output directory for generated content."""
        return folder_path

    @staticmethod
    def get_tov_cache_dir() -> str:
        """Get the TOV profile cache directory."""
        cache_dir = os.getenv("TOV_CACHE_DIR", "/tmp/tov_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    @classmethod
    def get_tov_file_id(cls, platform: str) -> Optional[str]:
        """Get the Google Drive file ID for a TOV profile."""
        return cls.TOV_FILE_IDS.get(platform.lower())

    @staticmethod
    def get_google_drive_script() -> str:
        """Get the path to the Google Drive API script."""
        # Find the project root by looking for .claude directory
        current = Path(__file__).resolve()
        while current != current.parent:
            if (current / ".claude").exists():
                return str(current / ".claude" / "scripts" / "google" / "google_drive.py")
            current = current.parent
        # Fallback
        return ".claude/scripts/google/google_drive.py"

    @staticmethod
    def get_templates_dir() -> str:
        """Get the path to the Gemini templates directory."""
        current = Path(__file__).resolve()
        while current != current.parent:
            if (current / ".claude").exists():
                return str(current / ".claude" / "templates" / "gemini" / "repurpose")
            current = current.parent
        return ".claude/templates/gemini/repurpose"

    @staticmethod
    def get_prompts_dir() -> str:
        """Deprecated: Use get_templates_dir() instead."""
        return Config.get_templates_dir()

    @staticmethod
    def get_api_key(key_name: str) -> Optional[str]:
        """Get an API key from environment variables."""
        return os.getenv(key_name)

    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Get the Gemini API key."""
        return cls.get_api_key("GEMINI_API_KEY")

    @classmethod
    def get_apitemplate_api_key(cls) -> Optional[str]:
        """Get the APITemplate.io API key."""
        return cls.get_api_key("APITEMPLATE_API_KEY")

    @classmethod
    def get_cloudconvert_api_key(cls) -> Optional[str]:
        """Get the CloudConvert API key."""
        return cls.get_api_key("CLOUDCONVERT_API_KEY")

    @classmethod
    def get_legnext_api_key(cls) -> Optional[str]:
        """Get the LegNext (Midjourney) API key."""
        return cls.get_api_key("LEGNEXT_API_KEY")

    @classmethod
    def validate_required_keys(cls, keys: list[str]) -> dict[str, bool]:
        """
        Validate that required API keys are present.

        Returns a dict of key_name -> is_present.
        """
        return {key: cls.get_api_key(key) is not None for key in keys}

    @classmethod
    def get_project_root(cls) -> Path:
        """Get the project root directory."""
        current = Path(__file__).resolve()
        while current != current.parent:
            if (current / ".claude").exists():
                return current
            current = current.parent
        return Path.cwd()

    @staticmethod
    def is_test_mode() -> bool:
        """Check if running in test mode."""
        return os.getenv("RUBY_TEST_MODE", "").lower() in ("1", "true", "yes")

    @staticmethod
    def get_test_output_dir() -> str:
        """Get the test output directory."""
        return os.getenv("RUBY_TEST_OUTPUT_DIR", "/tmp/ruby_test_output")

    @classmethod
    def get_timeout(cls, timeout_type: str) -> int:
        """Get a timeout value in seconds."""
        return cls.TIMEOUTS.get(timeout_type, 60)

    @classmethod
    def get_max_retries(cls) -> int:
        """Get the maximum number of retries for failed operations."""
        return cls.RETRY_CONFIG.get("max_retries", 3)

    @classmethod
    def get_retry_cooldown(cls) -> int:
        """Get the cooldown time between retries in seconds."""
        return cls.RETRY_CONFIG.get("cooldown_seconds", 15)

    @classmethod
    def print_config_summary(cls) -> None:
        """Print a summary of current configuration for debugging."""
        print("=" * 50)
        print("Ruby Repurpose Configuration Summary")
        print("=" * 50)
        print(f"the knowledge base agent Path: {cls.knowledge_base_path()}")
        print(f"TOV Cache Dir: {cls.get_tov_cache_dir()}")
        print(f"Project Root: {cls.get_project_root()}")
        print("-" * 50)
        print("API Keys Status:")
        keys = ["GEMINI_API_KEY", "APITEMPLATE_API_KEY", "CLOUDCONVERT_API_KEY", "LEGNEXT_API_KEY"]
        for key, present in cls.validate_required_keys(keys).items():
            status = "present" if present else "MISSING"
            print(f"  {key}: {status}")
        print("=" * 50)


# Convenience function for quick environment checks
def get_config() -> Config:
    """Get a Config instance."""
    return Config()


if __name__ == "__main__":
    # Test the configuration
    Config.print_config_summary()
