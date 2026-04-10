"""
Utility modules for FAIRSCAPE/RO-Crate integration.

This package contains helper modules for field prioritization,
informativeness scoring, validation, mapping management, and SSSOM.
Includes integration with standard sssom-py and linkml-map packages.
"""

from .field_prioritizer import FieldPrioritizer
from .validator import D4DValidator
from .mapping_loader import MappingLoader
from .rocrate_parser import ROCrateParser
from .informativeness_scorer import InformativenessScorer
from .d4d_builder import D4DBuilder
from .rocrate_merger import ROCrateMerger
from .sssom_reader import SSSOMReader, SSSOMMapping
from .sssom_integration import SSSOMIntegration

# Lazy import for linkml_map_integration to avoid import errors
# when linkml-map has dependency issues
_linkml_map_integration_module = None

def _get_linkml_map_integration():
    """Lazy import of linkml_map_integration module."""
    global _linkml_map_integration_module
    if _linkml_map_integration_module is None:
        try:
            from . import linkml_map_integration as _linkml_map_integration_module
        except Exception as e:
            import warnings
            warnings.warn(
                f"linkml_map_integration could not be imported: {e}\n"
                "LinkML-Map features will not be available.",
                ImportWarning
            )
            # Create a dummy module to prevent repeated import attempts
            class DummyModule:
                LinkMLMapIntegration = None
                create_sssom_from_tsv_mapping = None
                LINKML_MAP_AVAILABLE = False
            _linkml_map_integration_module = DummyModule()
    return _linkml_map_integration_module

def __getattr__(name):
    """Lazy loading of linkml-map integration classes."""
    if name in ('LinkMLMapIntegration', 'create_sssom_from_tsv_mapping'):
        module = _get_linkml_map_integration()
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'FieldPrioritizer',
    'D4DValidator',
    'MappingLoader',
    'ROCrateParser',
    'InformativenessScorer',
    'D4DBuilder',
    'ROCrateMerger',
    'SSSOMReader',
    'SSSOMMapping',
    'SSSOMIntegration',
    'LinkMLMapIntegration',
    'create_sssom_from_tsv_mapping',
]
