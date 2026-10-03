# Offline nested-support saved responses

`d4d evaluate support-results` checks saved evidence under the explicit
`nested_support_result_v1` protocol. It does not call a provider, execute a
planned request, use a judgement cache, or change an old plan. The v1/v2 planners
and SupportJudgeV2 remain separate instruments.

Prepare a descriptor from an existing `d4d-support-plan-v2` directory with
`--protocol nested_support_result_v1` and repeatable `--select TARGET_ID
ATTEMPT_ID`. Each selected target has one unique attempt. Fitness targets are
not eligible. The descriptor copies exact plan bytes and the selected records'
required artifact closure, reconstructs the schema specification and nested
inventory, and checks each selected complete request against its recipe. Schema
imports come only from captured bytes. Original source paths remain metadata;
they are never recreated or used to load today's schema.

The saved-response envelope is `nested_support_response_v1`. It contains exactly
`format`, `descriptor_sha256`, `target_id`, `attempt_id`, `request_sha256`, and
`message_base64`. The last field encodes the untouched native-message JSON bytes.
`package_response` below is a pure helper for an external capture harness. These
binding hashes are **caller declarations**: they detect unchanged envelope
replay into another request/attempt/record. They do not authenticate a provider
call or prevent a caller from inventing and relabelling evidence. A future
registered executor must capture this association at the actual call boundary.

The native-message adapter derives fields from those raw bytes. It requires an
assistant message, exact requested/reported model equality, `end_turn`, exactly
one text block containing a strict JSON object with exactly `verdict` and a
nonblank `reason`, and valid nonnegative integer input/output token counts.
Markdown fences, trailing prose, duplicate keys, nonfinite numbers, tool/refusal
blocks, unknown completion states and model aliases are refused. Optional
thinking/redacted-thinking blocks remain evidence. Missing usage remains
missing; it never becomes zero. There is no retry, best-of-N selection, model
alias mapping, or semantic truth certification.

`accept` preserves rejected raw evidence and exits nonzero for rejection. A
direct native-message file without an envelope is preserved and rejected with
an explicit missing-envelope reason. `recheck` reconstructs the outcome from
raw artifacts and returns success only when the saved assessment matches; a
correctly preserved rejection is still a valid artifact, not an accepted score.
Existing output directories, symlinks and aliases into input evidence are
refused. No command overwrites an existing destination.

`report` independently rechecks supplied results, refuses duplicate attempts and
foreign descriptors, and separates selected missing/rejected/accepted counts by
relationship edge and attribute value. Full-plan counts are labelled as declared
by the pinned manifest; unselected record artifacts are not reconstructed.
Fitness remains unscored. Even complete selected-response accounting leaves all
original calibration, context, instrument, transport and paid-readiness blockers
in place. This does not certify full-record schema validation or scientific
accuracy. Parents #3342/#2929 and calibration #3343 remain open.

## Invented fixture round trip

This example creates a new temporary Git fixture and makes no network or model
calls. The model name, usage, cap and verdict are invented software-test values.
They are not a quality measurement, calibrated instrument or production budget.
Run from an environment where this repository's `d4d` package is installed.

```bash
demo=$(mktemp -d)
python - "$demo" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
import yaml
from data_sheets_schema.support_plan import build_plan
root = Path(sys.argv[1]) / 'source'
root.mkdir()
(root / 'schema.yaml').write_text('''id: https://example.invalid/fixture
name: fixture
prefixes:
  linkml: https://w3id.org/linkml/
  ex: https://example.invalid/
imports: [linkml:types]
default_prefix: ex
classes:
  Dataset:
    attributes:
      title:
        range: string
      creators:
        range: Creator
        multivalued: true
        inlined_as_list: true
  Creator:
    attributes:
      name:
        range: string
''')
record = yaml.safe_dump({'title': 'River archive', 'creators': [{'name': 'Alex'}]}).encode()
bundle = b'FILE: invented.txt\nAlex prepared the River archive.\n'
(root / 'record.yaml').write_bytes(record)
(root / 'bundle.txt').write_bytes(bundle)
(root / 'provenance.yaml').write_text(yaml.safe_dump({
    'run': {'project': 'River', 'label': 'fixture_rep1', 'method': 'fixture'},
    'model': {'model': 'invented-generator'},
    'inputs': {'bundle_path': 'bundle.txt', 'bundle_md5': hashlib.md5(bundle).hexdigest()}}))
(root / 'roster.json').write_text(json.dumps({'jobs': [{
    'id': 'river-r20', 'input': 'record.yaml', 'project': 'River',
    'label': 'fixture_rep1', 'method': 'fixture', 'cohort': 'invented',
    'generation_rep': 1, 'purpose': 'primary', 'rubric': 'rubric20',
    'output': 'unmeasured.json', 'provenance': 'provenance.yaml'}],
    'pinned_files': {'record.yaml': hashlib.sha256(record).hexdigest()}}))
subprocess.run(['git', 'init', '-q', str(root)], check=True)
subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
subprocess.run(['git', '-C', str(root), '-c', 'user.name=Offline fixture',
                '-c', 'user.email=offline@example.invalid', 'commit', '-qm', 'Invented inputs'], check=True)
build_plan(root / 'roster.json', root.parent / 'plan', root=root, profile='neutral',
           schema_path=root / 'schema.yaml', model='fixture-judge', max_tokens=128,
           plan_version=2, artifact_kind='full')
PY

target=$(python - "$demo/plan/manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
print(next(t['id'] for t in m['targets'] if t['axis'] == 'grounding_v3'))
PY
)
d4d evaluate support-results prepare --plan "$demo/plan" \
  --output "$demo/descriptor" --protocol nested_support_result_v1 \
  --select "$target" invented-attempt

python - "$demo" <<'PY'
import json, sys
from pathlib import Path
from data_sheets_schema.nested_support_results import package_response
root = Path(sys.argv[1])
raw = json.dumps({'id': 'invented-message', 'type': 'message', 'role': 'assistant',
    'model': 'fixture-judge', 'stop_reason': 'end_turn',
    'usage': {'input_tokens': 10, 'output_tokens': 20},
    'content': [{'type': 'text', 'text': json.dumps({
        'verdict': 'supported', 'reason': 'Invented response for a software test.'})}]}).encode()
with (root / 'response-envelope.json').open('xb') as stream:
    stream.write(package_response((root / 'descriptor/descriptor.json').read_bytes(),
                                  attempt_id='invented-attempt', native_message=raw))
PY

d4d evaluate support-results accept --descriptor "$demo/descriptor" \
  --response "$demo/response-envelope.json" --attempt invented-attempt --output "$demo/result"
d4d evaluate support-results recheck --result "$demo/result"
d4d evaluate support-results report --descriptor "$demo/descriptor" --result "$demo/result"
```

The final report shows one selected accepted response, other plan targets
unselected, fitness unscored, and paid readiness still false. All bytes remain
available in the temporary directory for inspection.
