"""Compatibility entry point; implementation is in data_sheets_schema.rendering.human_readable_renderer."""
import sys
from data_sheets_schema.rendering.human_readable_renderer import *  # noqa: F401,F403
from data_sheets_schema.rendering import human_readable_renderer as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
