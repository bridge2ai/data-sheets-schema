#!/usr/bin/env python3
# Purpose: apply the reviewed NF3 path/replay repair without protected-file edits.
# Inputs: b6fba5946-derived source tree; outputs: five explicit source/test edits.
# Ref: #5213 NF3-1..4; 2026-10-30. Fails closed on changed preimages; local only.
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITS = {
    'src/data_sheets_schema/api_runner.py': [(
        '        else:\n            for _attr in ("bundle", "manifest", "chunk_manifest"):',
        '        elif not self._replay_only:\n'
        '            # Replay preserves the recorded spelling, even when inputs moved\n'
        '            # or the caller now runs from the original corpus root (#5213).\n'
        '            for _attr in ("bundle", "manifest", "chunk_manifest"):')],
    'tests/test_shared_generation_selection.py': [(
        '    directory = spec.bundle.parent\n',
        '    # Registration authority is absolute even when input paths are relative.\n'
        '    directory = Path(spec.bundle).absolute().parent\n')],
    'tests/test_shared_generation_cli.py': [(
        "    path=base.bundle.parent/'roster.json';path.write_bytes",
        "    path=Path(base.bundle).absolute().parent/'roster.json';path.write_bytes")],
    'tests/test_profiles.py': [(
        '        self.assertIn(f"--manifest {STUDY_MANIFEST}", line)\n',
        '        import shlex\n'
        '        command = shlex.split(line)\n'
        '        self.assertEqual(command.count("--manifest"), 1)\n'
        '        selected = command[command.index("--manifest") + 1]\n'
        '        self.assertNotEqual(selected, "none")\n'
        '        self.assertEqual(Path(selected).absolute(), STUDY_MANIFEST.absolute())\n'), (
        '\n                  "inputs": {"bundle_path": str(bundle), "source_manifest": {"path": None},\n',
        '\n                  "inputs": {"bundle_path": str(spec.bundle), "source_manifest": {"path": None},\n')],
    'src/data_sheets_schema/cli/provenance.py': [(
        '@provenance.command("backfill-spec")\n',
        '''def _backfill_input_spellings(value: Path | None, owner: Path | None) -> tuple[Path | None, ...]:
    """Bounded lexical candidates; only the complete original hash admits one.

    An unknown owner is not inferred from cwd. Never resolve symlinks, erase
    traversal components or search disk for a replacement. Original spellings
    remain candidates, including explicit historical spellings containing '..'.
    """
    if value is None:
        return (None,)
    value = Path(value)
    if owner is None or not owner.is_absolute() or ".." in owner.parts or ".." in value.parts:
        return (value,)
    if value.is_absolute():
        try:
            alternate = value.relative_to(owner)
        except ValueError:
            return (value,)
    else:
        alternate = owner / value
    return (value,) if alternate == value else (value, alternate)


@provenance.command("backfill-spec")
'''), (
        '''    for delta, render_version, selected_chunks, selected_manifest, selected_profile, destinations, scoped_chunks in product(
            (0, -1, 1, -2, 2), (8, 7, 6, 5, 4, 3, 2, 1), chunk_choices, manifest_choices, profile_choices,
            destination_choices, (True, False)):
''',
        '''    def candidates():
        # Finish the entire original traversal before adding spelling alternatives.
        # This preserves historical first-match ordering and profile decisions.
        for alternate in (False, True):
            for delta, version, selected_chunks, selected_manifest, selected_profile, selected_destinations, scoped in product(
                    (0, -1, 1, -2, 2), (8, 7, 6, 5, 4, 3, 2, 1), chunk_choices,
                    manifest_choices, profile_choices, destination_choices, (True, False)):
                original = (Path(bundle), selected_chunks, selected_manifest)
                spellings = (product(*(_backfill_input_spellings(value, owner) for value in original))
                             if alternate else (original,))
                for selected_bundle, candidate_chunks, candidate_manifest in spellings:
                    if alternate and (selected_bundle, candidate_chunks, candidate_manifest) == original:
                        continue
                    yield (delta, version, selected_bundle, candidate_chunks, candidate_manifest,
                           selected_profile, selected_destinations, scoped)

    for delta, render_version, selected_bundle, selected_chunks, selected_manifest, selected_profile, destinations, scoped_chunks in candidates():
'''), (
        '            "arm": _ARMS[arm][0], "bundle": str(bundle), "condition": condition,\n',
        '            "arm": _ARMS[arm][0], "bundle": str(selected_bundle), "condition": condition,\n')],
}


def main():
    pending = {}
    for name, edits in EDITS.items():
        text = (ROOT / name).read_text()
        for before, after in edits:
            if text.count(before) != 1:
                raise SystemExit(f'Expected one unchanged preimage in {name}')
            text = text.replace(before, after)
        pending[name] = text
    for name, text in pending.items():
        (ROOT / name).write_text(text)
        print(name)


if __name__ == '__main__':
    main()
