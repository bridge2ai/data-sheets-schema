"""Reusable own-checkout import witness for offline native tests.

Pure inspection of import metadata; does not launch processes or alter imports.
"""
from pathlib import Path
import sys


def origin_witness(root):
    import data_sheets_schema
    package = Path(root) / "src/data_sheets_schema"
    raw_paths = [str(path) for path in data_sheets_schema.__path__]
    paths = [str(Path(path).resolve()) for path in raw_paths]
    if not paths or any(path != str(package) for path in paths):
        raise RuntimeError("mixed project namespace: " + repr(paths))
    editable = [repr(finder) for finder in sys.meta_path if "__editable__" in repr(finder)]
    if editable:
        raise RuntimeError("editable-install import finder is active")
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name != "data_sheets_schema" and not name.startswith("data_sheets_schema."):
            continue
        path = getattr(module, "__file__", None)
        if path is not None:
            resolved = Path(path).resolve()
            if not resolved.is_relative_to(package):
                raise RuntimeError("foreign project module: " + name + " " + str(resolved))
            origins[name] = str(resolved)
        for item in getattr(module, "__path__", ()):
            if not Path(item).resolve().is_relative_to(package):
                raise RuntimeError("foreign project subpackage: " + name)
    return {"python": sys.executable, "prefix": sys.prefix,
            "package_paths_raw": raw_paths, "package_paths": paths,
            "module_origins": origins, "sys_path": list(sys.path),
            "editable_finders": editable,
            "no_user_site": bool(sys.flags.no_user_site),
            "safe_path": bool(sys.flags.safe_path),
            "dont_write_bytecode": sys.dont_write_bytecode}
