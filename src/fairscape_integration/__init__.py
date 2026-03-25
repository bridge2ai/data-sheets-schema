"""
FAIRSCAPE Models Integration

This module integrates FAIRSCAPE Pydantic models for RO-Crate generation
and validation, replacing custom JSON-LD structures.

Usage:
    from fairscape_integration import create_d4d_rocrate, validate_rocrate
    
    # Create RO-Crate from D4D data
    rocrate = create_d4d_rocrate(d4d_dict)
    
    # Validate RO-Crate
    is_valid, errors = validate_rocrate(rocrate)
"""

# Try to import FAIRSCAPE models
try:
    # Add fairscape_models to path
    import sys
    from pathlib import Path
    
    fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
    if fairscape_path.exists() and str(fairscape_path) not in sys.path:
        sys.path.insert(0, str(fairscape_path))
    
    from fairscape_models.rocrate import ROCrateV1_2
    from fairscape_models.dataset import Dataset
    from fairscape_models.fairscape_base import FairscapeBaseModel
    
    FAIRSCAPE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: FAIRSCAPE models not available: {e}")
    FAIRSCAPE_AVAILABLE = False
    ROCrateV1_2 = None
    Dataset = None
    FairscapeBaseModel = None

__all__ = [
    'FAIRSCAPE_AVAILABLE',
    'ROCrateV1_2',
    'Dataset',
    'FairscapeBaseModel'
]
