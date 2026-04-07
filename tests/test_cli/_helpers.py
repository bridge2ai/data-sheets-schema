"""Helpers for CLI tests."""

from types import ModuleType


def build_module_tree(qualified_name, **attrs):
    """Build a fake module tree suitable for patching into ``sys.modules``."""
    modules = {}
    parts = qualified_name.split(".")

    for index in range(1, len(parts) + 1):
        module_name = ".".join(parts[:index])
        module = modules.setdefault(module_name, ModuleType(module_name))

        if index > 1:
            parent_name = ".".join(parts[: index - 1])
            setattr(modules[parent_name], parts[index - 1], module)

    for name, value in attrs.items():
        setattr(modules[qualified_name], name, value)

    return modules
