# Declared model-family disclosure

`report_model_disclosure.py` is an additive offline report for explicitly named
rating JSON files. It accepts semantic and legacy hybrid ratings, keeps repeated
ratings as separate rows, and never computes or changes scores. Its
`model-disclosure-v1` output is separate from the registered semantic comparison
report and its archived implementations. Existing summary scripts and reports
retain their behavior.

```bash
PYTHONPATH=src poetry run python scripts/report_model_disclosure.py \
  rating.json older-hybrid-rating.json \
  --generation-binding rating.json generated.yaml provenance.yaml \
  --root /path/to/the/recorded/tree --format json --output new-disclosure.json
```

Omit `--output` to print to stdout. Markdown is the default; `--format csv` and
`--format json` expose the same per-rating fields. Output files must be new;
existing files, including symlinks and hardlinks, are refused. Input arguments
use the caller's normal filesystem paths. `--root` anchors relative paths
*recorded inside* the evaluation and provenance; it defaults to the current
working directory. It does not select an ambient study or discover records.

Each repeatable `--generation-binding EVALUATION INPUT PROVENANCE` names one
explicit association. It must name an evaluation included in the report and
cannot be repeated for that file. A repeated evaluation argument still produces
another rating row with the same supplied binding. Named files are captured
once; parsing and reported hashes use those captured bytes. Every row includes
its evaluation identity/hash, declared evaluator and evaluation type, supplied
input/provenance identities and hashes, generator association checks, model
families and `yes`, `no` or `unknown` same-family status.

An association requires a recorded input path or verified evaluation-input hash,
a matching provenance `outputs.full.path` or `outputs.core.path`, agreement with
every evaluation-declared project/method/label, and a recorded generation model.
Missing evidence produces an explicit unknown row. A supplied contradictory
binding refuses the report before writing an output. Bare filename-only
`d4d_file` values require a matching input hash; they cannot establish association
on their own. Missing historical provenance output hashes are permitted and
shown as absent checks. Any supplied output SHA256/MD5 or byte count must match.
These checks associate supplied local declarations; they do not authenticate
provider responses, establish an original registration, or prove absence of
manual edits to historical files.

The v1 input-hash contract checks `metadata.input_sha256`,
`metadata.d4d_file_hash` and top-level `input_sha256` as SHA256. The legacy rubric
schemas and the hybrid/API writers define `d4d_file_hash` as SHA256; its historical
`sha256:` prefix is accepted. All declared hashes must match, not just one. A
bare 32-character value is not guessed to be MD5. Provenance output `sha256` and
`md5` fields explicitly select their own algorithms. The supported recorded
input paths are `d4d_file`, `input_file` and `input_path` at the top level or in
`metadata`; unrelated context/rubric/bundle hashes are not input hashes.

Evaluator identity uses the shared precedence `model.evaluator_model`,
`model.model_id`, then `model.name`. Generator identity comes only from the
associated provenance's `model.model`, then `model.name`. A method such as
`gpt5`, a filename, evaluation `metadata.generator`, current configuration or
default model never supplies a generator identity. Missing or malformed model
values remain unknown. Known LLM evaluation types (`semantic_llm_judge`,
`llm_as_judge`, `llm_judge`, `llm`) and legacy absent types permit family lookup;
other declared types remain visible with unknown evaluator family, even if their
display name resembles an LLM. `model.evaluation_type` takes display precedence
over the top-level field; both declarations are retained. Conflicting or
malformed declarations conservatively keep family comparison unknown, including
false, empty strings and collection-valued types. Families use the existing declared-model helper,
so `google/claude-...` denotes the Claude family regardless of routing vendor.

This family flag does not measure self-preference, calibration or evaluator
independence. An unknown model is not evidence of a different family. Historical
output refresh/consumer integration remains under #3327, and empirical
cross-family calibration remains separate (#3328).
