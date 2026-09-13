"""Compatibility entry point; implementation is in data_sheets_schema.rendering.process_text_files."""
import sys
from data_sheets_schema.rendering.process_text_files import *  # noqa: F401,F403
from data_sheets_schema.rendering import process_text_files as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
