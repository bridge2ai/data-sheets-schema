"""Project constants for D4D data sheets schema.

This module centralizes project names and paths used throughout the codebase.
"""

from pathlib import Path

# Project names
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]

# Base data directory
DATA_DIR = Path("data")

# Project-specific directory paths
PROJECT_PATHS = {
    "raw": DATA_DIR / "raw",
    "preprocessed_individual": DATA_DIR / "preprocessed" / "individual",
    "preprocessed_concatenated": DATA_DIR / "preprocessed" / "concatenated",
    "d4d_individual": DATA_DIR / "d4d_individual",
    "d4d_concatenated": DATA_DIR / "d4d_concatenated",
    "d4d_html_individual": DATA_DIR / "d4d_html" / "individual",
    "d4d_html_concatenated": DATA_DIR / "d4d_html" / "concatenated",
    "evaluation": DATA_DIR / "evaluation",
    "evaluation_individual": DATA_DIR / "evaluation_individual",
    "evaluation_llm": DATA_DIR / "evaluation_llm",
}

# Helper functions for project-specific paths
def get_raw_path(project: str) -> Path:
    """Get raw data path for a project."""
    return PROJECT_PATHS["raw"] / project

def get_preprocessed_path(project: str) -> Path:
    """Get preprocessed individual path for a project."""
    return PROJECT_PATHS["preprocessed_individual"] / project

def get_d4d_individual_path(method: str, project: str) -> Path:
    """Get D4D individual path for a method and project."""
    return PROJECT_PATHS["d4d_individual"] / method / project

def get_d4d_concatenated_path(method: str) -> Path:
    """Get D4D concatenated path for a method."""
    return PROJECT_PATHS["d4d_concatenated"] / method
