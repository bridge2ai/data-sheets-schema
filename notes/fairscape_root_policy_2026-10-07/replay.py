"""Replay the #4586 compatibility corpus into a fresh review directory."""
import argparse, contextlib, hashlib, io, json, sys, zipfile
from pathlib import Path
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = args.repo.resolve()
out = args.output.resolve()
sys.path.insert(0, str(source / 'src'))

from data_sheets_schema.rocrate_map import FULL_SCHEMA, TARGET_CLASS, MAPPING_TSV, load_mapping, map_crate
from data_sheets_schema.schema_view import shared_view
from fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter, root_data_entity, record_validator

out.mkdir(exist_ok=False)
paths = {
    'profile': 'data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json',
    'cm4ai_roundtrip': 'data/ro-crate/examples/CM4AI_roundtrip.json',
    'voice_roundtrip': 'data/ro-crate/examples/voice_d4d_to_fairscape.json',
    'voice_example': 'data/ro-crate/examples/voice_fairscape_test.json',
    'CHORUS': 'data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json',
    'VOICE': 'data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json',
    'CM4AI_reduced': 'data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json',
}
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
inputs = {name: ((source / path).read_bytes(), {'path': path}) for name, path in paths.items()}
archive = source / 'data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip'
member = 'cm4ai_release_metadata/ro-crate-metadata.json'
with zipfile.ZipFile(archive) as z:
    inputs['CM4AI'] = (z.read(member), {'path': str(archive.relative_to(source)),
        'archive_sha256': digest(archive.read_bytes()), 'member': member})
validator = record_validator(str(source / FULL_SCHEMA))
view = shared_view(source / FULL_SCHEMA)
rows = load_mapping(source / MAPPING_TSV)
summary = {}
for name, (raw, binding) in inputs.items():
    crate = json.loads(raw)
    converter = FairscapeToD4DConverter()
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        record = converter.convert(crate)
    target = out / (name + '.yaml')
    target.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True))
    readback = yaml.safe_load(target.read_text())
    errors = [r.message for r in validator.validate(readback, TARGET_CLASS).results]
    assert not errors, (name, errors)
    (out / (name + '.dropped.json')).write_text(json.dumps(converter.dropped, indent=2)+'\n')
    (out / (name + '.conversion.log')).write_text(printed.getvalue())
    reversed_crate = dict(crate, **{'@graph': list(reversed(crate['@graph']))})
    with contextlib.redirect_stdout(io.StringIO()):
        reverse_record = FairscapeToD4DConverter().convert(reversed_crate)
    canonical = lambda r: {**r, **({'file_collections': sorted(r['file_collections'], key=lambda x: encoded(x))}
                                  if 'file_collections' in r else {})}
    assert root_data_entity(crate['@graph']) == root_data_entity(reversed_crate['@graph']), name
    assert canonical(record) == canonical(reverse_record), name
    binding.update(input_sha256=digest(raw), root_id=root_data_entity(crate['@graph']).get('@id'),
        output_sha256=digest(target.read_bytes()), record_sha256=digest(encoded(record)),
        dropped_sha256=digest(encoded(converter.dropped)), validation='PASS',
        reversal='same root and contents; file_collections compared as a multiset')
    if name in ('CHORUS', 'CM4AI', 'VOICE'):
        static = map_crate(crate['@graph'], rows, view).record
        assert not validator.validate(static, TARGET_CLASS).results, name
        assert static == map_crate(reversed_crate['@graph'], rows, view).record, name
        binding['static_record_sha256'] = digest(encoded(static))
        (out / (name + '.static.yaml')).write_text(yaml.safe_dump(static, sort_keys=False, allow_unicode=True))
    summary[name] = binding
(out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
