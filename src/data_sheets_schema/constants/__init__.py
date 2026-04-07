"""Centralized constants for D4D data sheets schema.

This package provides a single import point for all constants used throughout
the codebase, replacing scattered hardcoded values.

Usage:
    from data_sheets_schema.constants import PROJECTS, METHODS, MODULE_MAP

Example:
    from data_sheets_schema.constants import (
        PROJECTS,
        METHODS,
        get_raw_path,
        get_d4d_individual_path
    )

    for project in PROJECTS:
        raw_path = get_raw_path(project)
        print(f"Processing {project} from {raw_path}")
"""

# Re-export all constants from submodules
from .projects import (
    PROJECTS,
    DATA_DIR,
    PROJECT_PATHS,
    get_raw_path,
    get_preprocessed_path,
    get_d4d_individual_path,
    get_d4d_concatenated_path,
)

from .methods import (
    METHODS,
    CURRENT_METHOD,
    LEGACY_METHODS,
    API_METHODS,
    INTERACTIVE_METHODS,
    REFERENCE_METHODS,
)

from .schemas import (
    SCHEMA_DIR,
    SCHEMA_PATH,
    SCHEMA_FULL_PATH,
    MODULE_MAP,
    D4D_MODULES,
    BASE_MODULE,
)

from .evaluation import (
    RUBRIC_DIR,
    RUBRIC10_PATH,
    RUBRIC20_PATH,
    RUBRIC_TYPES,
    RUBRIC10_MAX_ELEMENTS,
    RUBRIC10_SUBELEMENTS_PER_ELEMENT,
    RUBRIC10_MAX_SCORE,
    RUBRIC20_MAX_QUESTIONS,
    RUBRIC20_MAX_SCORE,
    EVALUATION_TYPES,
    LLM_EVAL_TEMPERATURE,
    LLM_EVAL_MODEL,
)

__all__ = [
    # Projects
    "PROJECTS",
    "DATA_DIR",
    "PROJECT_PATHS",
    "get_raw_path",
    "get_preprocessed_path",
    "get_d4d_individual_path",
    "get_d4d_concatenated_path",
    # Methods
    "METHODS",
    "CURRENT_METHOD",
    "LEGACY_METHODS",
    "API_METHODS",
    "INTERACTIVE_METHODS",
    "REFERENCE_METHODS",
    # Schemas
    "SCHEMA_DIR",
    "SCHEMA_PATH",
    "SCHEMA_FULL_PATH",
    "MODULE_MAP",
    "D4D_MODULES",
    "BASE_MODULE",
    # Evaluation
    "RUBRIC_DIR",
    "RUBRIC10_PATH",
    "RUBRIC20_PATH",
    "RUBRIC_TYPES",
    "RUBRIC10_MAX_ELEMENTS",
    "RUBRIC10_SUBELEMENTS_PER_ELEMENT",
    "RUBRIC10_MAX_SCORE",
    "RUBRIC20_MAX_QUESTIONS",
    "RUBRIC20_MAX_SCORE",
    "EVALUATION_TYPES",
    "LLM_EVAL_TEMPERATURE",
    "LLM_EVAL_MODEL",
]
