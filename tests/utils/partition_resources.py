"""#5485, 2026-11-04: copy declared partition resources into selected test trees.

Inputs: the source checkout's declaration roster and verified sizing/calibration
pins. Outputs: identical files under the selected temporary test tree.
"""
from pathlib import Path
import shutil

from scripts import build_api_registrations as builder


ROOT = Path(__file__).resolve().parents[2]


def copy_partition_resources(selected, *, source_root=ROOT):
    """Copy the authoritative roster and its evidence without a caller fallback."""
    source_root, selected = Path(source_root).resolve(), Path(selected)
    sources = [source_root / name for name in builder.AUDIT_PARTITION_FILES]
    for declaration in builder.partition_profiles(root_dir=source_root).values():
        pins = [*declaration['sizing_record'].values(),
                *declaration.get('calibration_bundle', {}).values()]
        sources.extend(Path(pin['path']) for pin in pins)
    for source in dict.fromkeys(sources):
        target = selected / source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
