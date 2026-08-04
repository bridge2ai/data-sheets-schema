"""Project constants for D4D data sheets schema.

This module centralizes project names and paths used throughout the codebase.
"""

from pathlib import Path

# Project names.
#
# `VOICE` is the adult/main Bridge2AI-Voice dataset. `VOICE_PEDIATRIC` is the
# companion pediatric dataset — its own DOI (10.13026/h995-bt35), its own
# protocol, its own Research Ethics Board approval, published separately on
# PhysioNet. It was being represented as a nested object inside VOICE's
# `related_datasets`, which is what made no VOICE replicate validate (#292);
# a dataset with those three things is its own datasheet.
#
# Both are documented in the same source corpus, so they share a bundle and are
# distinguished by the manifest line rather than by different inputs.
#
# `VOICE` is not renamed to `VOICE_main`. 198 of the paths that would move are
# archived records, archived precisely because their provenance could not be
# verified — rewriting the project field of runs that were set aside for
# provenance reasons is the opposite of what archiving them was for. The live
# rename is available as its own migration; see the note in NEXT_TASKS.
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]

#: Datasets that are separate records but share a source corpus. Analyses that
#: treat projects as independent samples should know these two are not.
SHARED_CORPUS_GROUPS = {"bridge2ai_voice": ["VOICE", "VOICE_PEDIATRIC"]}

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
