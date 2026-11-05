#!/usr/bin/env python3
# Purpose: apply bounded helper generalizations for #5483 J-a, 2026-11-05.
# Inputs: baseline checkout; outputs: helper, caller and documentation edits.
from pathlib import Path


def edit(name, replacements):
    path = Path(name)
    text = path.read_text()
    for old, new in replacements:
        assert old in text, (name, old)
        text = text.replace(old, new)
    path.write_text(text)


edit('scripts/adhoc/d41_request_parity_20261026.py', [
    ('real CHORUS inputs', 'caller-selected project inputs'),
    ('def _fixture(root, fixture, registration_snapshot):', 'def _fixture(root, fixture, registration_snapshot, *, project, partition, context_path):'),
    ("build_registration('CHORUS',", 'build_registration(project,'),
    ("context_path=root / 'data/omission_contexts/chorus_omission_context.json',", 'context_path=context_path,'),
    ("partition='chorus'", 'partition=partition'),
    ('def capture(root, code_root, fixture, output, mode):', 'def capture(root, code_root, fixture, output, mode, *, project, partition, context_path):'),
    ("_fixture(root, fixture, output / 'registration.json')", "_fixture(root, fixture, output / 'registration.json',\n        project=project, partition=partition, context_path=context_path)"),
    ('def compare(root, workdir):', 'def compare(root, workdir, *, project, partition, context_path):'),
    ("'--out', str(out)]", "'--out', str(out),\n                   '--project', project, '--partition', partition, '--context-path', str(context_path.resolve())]"),
    ("'format': 'd41_chorus_request_parity_v1'", "'format': f'd41_{project.lower()}_request_parity_v1'"),
    ("'scope': 'Exact generic_v10/shared-v1 CHORUS request", "'scope': f'Exact generic_v10/shared-v1 {project} request"),
    ("parser.add_argument('--workdir', type=Path)", "parser.add_argument('--workdir', type=Path)\n    parser.add_argument('--project', required=True)\n    parser.add_argument('--partition', required=True)\n    parser.add_argument('--context-path', type=Path, required=True)"),
    ('capture(args.root, args.code_root, args.fixture, args.out, args.capture)', 'capture(args.root, args.code_root, args.fixture, args.out, args.capture,\n            project=args.project, partition=args.partition, context_path=args.context_path.resolve())'),
    ('compare(args.root, args.workdir)', 'compare(args.root, args.workdir, project=args.project,\n            partition=args.partition, context_path=args.context_path.resolve())'),
])
edit('tests/test_d41_request_parity.py', [("parity.compare(ROOT, tmp_path / 'parity')", "parity.compare(ROOT, tmp_path / 'parity', project='CHORUS',\n        partition='chorus', context_path=ROOT / 'data/omission_contexts/chorus_omission_context.json')")])
edit('scripts/adhoc/retain_d41_legacy_evidence_20261029.py', [
    ('            for name in ("controller_traceback.txt", "result.json"):', '            attempts = [p for p in (args.runtime_ci_root / case / "registration/attempts").glob("*") if p.is_dir()]\n            assert len(attempts) == 1, f"expected exactly one attempt directory: {attempts}"\n            for name in ("controller_traceback.txt", "result.json"):'),
    ('args.runtime_ci_root / case / "registration/attempts/CHORUS_direct_rep1" / name', 'attempts[0] / name'),
])
edit('scripts/adhoc/profile_admission_r3_20261104.py', [
    ("CASE = ('tests/test_report_admission.py::'\n        'test_chorus_wire_is_byte_identical_without_admission_and_is_what_was_counted')\n", ''),
    ('def run(label):', 'def run(label, case):'),
    ("'worker', label]", "'worker', label, '--case', case]"),
    ('def worker(label):', 'def worker(label, case):'),
    ('case=CASE', 'case=case'), ('pytest.main([CASE,', 'pytest.main([case,'),
    ("parser.add_argument('label', choices=COMMITS)", "parser.add_argument('label', choices=COMMITS)\n    parser.add_argument('--case', required=True)"),
    ("run(args.label) if args.mode == 'run' else worker(args.label)", "run(args.label, args.case) if args.mode == 'run' else worker(args.label, args.case)"),
])
edit('notes/ci_timing_refresh_2026-11-04/README.md', [
    ('`profile_admission_r3_20261104.py run g1` and then `run bc1g2` run the same', '`profile_admission_r3_20261104.py run g1 --case tests/test_report_admission.py::test_chorus_wire_is_byte_identical_without_admission_and_is_what_was_counted`\nand then the same command with `run bc1g2` run the same'),
])
