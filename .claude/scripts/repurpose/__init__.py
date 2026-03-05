"""
CEO Content Engine - Repurpose Module

This module provides content repurposing functionality for Ruby agent,
migrated from the N8N-based CEO Content Engine.

Main components:
- config: Environment and configuration management
- manifest: File-based job tracking (_manifest.json)
- extraction: Insight extraction from transcripts
- generators: Platform-specific content generators
- utils: Utility modules (TOV, the knowledge base agent, external APIs)
"""

from .config import Config, get_config

__version__ = "2.0.0"
__all__ = ["Config", "get_config"]
