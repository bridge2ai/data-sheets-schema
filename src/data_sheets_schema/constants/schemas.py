"""Schema-related constants for D4D data sheets.

This module centralizes schema paths and module mappings.
"""

from pathlib import Path

# Schema paths
SCHEMA_DIR = Path("src") / "data_sheets_schema" / "schema"
SCHEMA_PATH = SCHEMA_DIR / "data_sheets_schema.yaml"
SCHEMA_FULL_PATH = SCHEMA_DIR / "data_sheets_schema_all.yaml"

# D4D module prefix to module name mapping
# Source: Extracted from schema_stats.py lines 61-78
MODULE_MAP = {
    'd4dmotivation': 'D4D_Motivation',
    'd4dcomposition': 'D4D_Composition',
    'd4dcollection': 'D4D_Collection',
    'd4dpreprocessing': 'D4D_Preprocessing',
    'd4duses': 'D4D_Uses',
    'd4ddistribution': 'D4D_Distribution',
    'd4dmaintenance': 'D4D_Maintenance',
    'd4dethics': 'D4D_Ethics',
    'd4dhuman': 'D4D_Human',
    'd4ddatagovernance': 'D4D_Data_Governance',
    'd4dvariables': 'D4D_Variables',
    'd4dmetadata': 'D4D_Metadata',
    'd4dminimal': 'D4D_Minimal',
    'd4dbase': 'D4D_Base_import',
    'linkml': 'LinkML_Core',
}

# D4D module list (in order)
D4D_MODULES = [
    'D4D_Motivation',
    'D4D_Composition',
    'D4D_Collection',
    'D4D_Preprocessing',
    'D4D_Uses',
    'D4D_Distribution',
    'D4D_Maintenance',
    'D4D_Human',
    'D4D_Ethics',
    'D4D_Data_Governance',
    'D4D_Metadata',
    'D4D_Minimal',
]

# Base module
BASE_MODULE = 'D4D_Base_import'
