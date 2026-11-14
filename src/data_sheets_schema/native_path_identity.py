"""Read-only native path containment, 2026-11-08 (U4b A4 P2-2).

Resolve links and compare existing device/inode ancestors without rewriting
case. Missing prospective components are permitted; inaccessible, dangling or
non-directory ancestors are not evidence of a safe fresh location. This is an
admission check, not a filesystem reservation against concurrent replacement.
"""
from pathlib import Path
import stat
import unicodedata


def _identity(info):
    return info.st_dev, info.st_ino


def _location(value):
    path = Path(value)
    if not path.is_absolute() or '\0' in str(path) or '..' in path.parts:
        raise ValueError('physical containment requires an absolute path without parent traversal')
    current, suffix = path, []
    try:
        while True:
            try:
                current.lstat()
                break
            except FileNotFoundError:
                if current == current.parent:
                    raise ValueError('physical containment has no existing ancestor')
                suffix.insert(0, current.name)
                current = current.parent
        before = current.stat()  # A dangling link must not become a prospective leaf.
        if suffix and not stat.S_ISDIR(before.st_mode):
            raise ValueError('physical containment prospective parent is not a directory')
        anchor = current.resolve(strict=True)
        if _identity(anchor.stat()) != _identity(before):
            raise ValueError('physical containment ancestor changed while resolving')
        ancestors = []
        for parent in (anchor, *anchor.parents):
            ancestors.append(_identity(parent.stat()))
        if _identity(current.stat()) != _identity(before):
            raise ValueError('physical containment ancestor changed while inspecting')
    except (OSError, RuntimeError) as exc:
        raise ValueError('physical containment could not verify an existing ancestor') from exc
    return anchor.joinpath(*suffix), _identity(before), tuple(suffix), tuple(ancestors)


def _contains(container, target):
    source_path, source_inode, source_suffix, _ = container
    target_path, target_inode, target_suffix, target_ancestors = target
    if target_path == source_path or source_path in target_path.parents:
        return True
    if not source_suffix and source_inode in target_ancestors:
        return True
    if source_inode == target_inode:
        if target_suffix[:len(source_suffix)] == source_suffix:
            return True
        # Neither missing spelling has an inode yet. A case-insensitive
        # filesystem could make these a future ancestor/descendant pair;
        # refuse ambiguity rather than rewriting either path or guessing the
        # volume's case rules from the platform name.
        fold = lambda parts: tuple(unicodedata.normalize('NFC', name).casefold() for name in parts)
        source_fold, target_fold = fold(source_suffix), fold(target_suffix)
        if target_fold[:len(source_fold)] == source_fold:
            raise ValueError('physical containment has ambiguous prospective path aliases')
    return False


def contains(container, target):
    """Return whether target equals or is beneath container physically."""
    return _contains(_location(container), _location(target))


def overlaps(first, second):
    """Return physical equality or containment in either direction."""
    first, second = _location(first), _location(second)
    return _contains(first, second) or _contains(second, first)
