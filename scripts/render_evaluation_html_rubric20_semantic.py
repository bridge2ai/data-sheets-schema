"""Compatibility entry point; implementation is in data_sheets_schema.rendering.rubric20_semantic."""
import sys
from data_sheets_schema.rendering.rubric20_semantic import *  # noqa: F401,F403
from data_sheets_schema.rendering import rubric20_semantic as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
