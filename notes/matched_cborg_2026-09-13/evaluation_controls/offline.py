"""Provider-free exact-file presence and mechanical review of a composite pair."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from registration import BudgetStop, canonical_path, read_json, sha, source_artifacts, verify_manifest
from budgeted_cborg import write_new


def run_checks(registration_path, destination):
    registration_path = canonical_path(str(registration_path), exists=True)
    manifest = read_json(registration_path)
    if manifest.get('schema_version') != 2:
        raise BudgetStop('composite offline checks require the explicit schema-v2 source')
    verify_manifest(manifest, registration_path, sha(registration_path))
    destination = canonical_path(str(destination))
    if destination.exists():
        raise BudgetStop('offline evidence destination already exists; never overwrite')
    frozen = {**manifest['pinned_files'], str(registration_path):sha(registration_path)}
    attempts = Path(manifest['attempts_dir'])
    if destination == attempts or attempts in destination.parents:
        raise BudgetStop('offline checks cannot write into a paid attempt')
    for name in frozen:
        path = Path(name)
        if path == destination or path in destination.parents or destination in path.parents:
            raise BudgetStop('offline destination overlaps immutable inputs')
    source = manifest['source_pair']
    phase = read_json(source['finalization']['registration']['path'])
    from finalization_controls.contract import validate_final
    from data_sheets_schema.evaluation.evaluate_d4d import D4DEvaluator
    from data_sheets_schema.evaluation_context import load_context
    from data_sheets_schema.duplicate_keys import duplicate_keys_in
    from data_sheets_schema.verifiable import check_record, identifier_slots
    from data_sheets_schema.evaluation_context import load_document
    mechanical = validate_final(phase)
    if mechanical.get('checked') is not True:
        raise BudgetStop('composite mechanical checks were not completed')
    bundle = Path(source['bundle']['path']).read_text()
    # Definitions are the actual presence instrument; separate from agent/API rubrics.
    repository = Path(manifest['repository'])
    rubric10 = repository/'data/rubric/rubric10.txt'
    rubric20 = repository/'data/rubric/rubric20.txt'
    if str(rubric10) not in frozen or str(rubric20) not in frozen:
        raise BudgetStop('presence instruments are not pinned')
    evaluator = D4DEvaluator(str(rubric10), str(rubric20), context=load_context(Path(manifest['context_path'])))
    results = {}
    for variant, artifact in source_artifacts(manifest).items():
        path = Path(artifact['path'])
        if duplicate_keys_in(path):
            raise BudgetStop('accepted input contains duplicate YAML keys')
        schema = Path(phase['inputs']['full_schema' if variant == 'full' else 'core_schema'])
        record, digest = load_document(path)
        presence = evaluator.evaluate_d4d_file(path, manifest['project'], manifest['method'])
        results[variant] = {'class_name':'Dataset' if variant == 'full' else 'CoreDataset',
            'input_sha256':digest, 'presence':asdict(presence),
            'literal_grounding':asdict(check_record(record,bundle,project=manifest['project'],skip_slots=identifier_slots(schema)))}
    if any(sha(name) != expected for name, expected in frozen.items()):
        raise BudgetStop('immutable evidence changed during offline checks')
    destination.mkdir(parents=True,exist_ok=False)
    outputs = {}
    for variant, value in results.items():
        path = destination/(variant+'.json');write_new(path,value);outputs[str(path)] = sha(path)
    check_path = destination/'mechanical_checks.json';write_new(check_path,mechanical);outputs[str(check_path)] = sha(check_path)
    report = {'kind':'d4d_composite_offline_evaluation','schema_version':1,
        'registration_sha256':sha(registration_path),'created_at':datetime.now(timezone.utc).isoformat(),
        'source_pair':source,'input_files':2,'presence_rubric_cells':4,
        'source_context_sha256':sha(manifest['context_path']),
        'presence_instrument_sha256':evaluator.instrument['sha256'],
        'checked':True,'mechanical_passed':mechanical.get('passed') is True,
        'artifacts':outputs,'provider_calls':0,'token_count_calls':0,'accounting_ownership_claimed':False,
        'scientific_acceptance':False,
        'scope':'Exact accepted final pair; inherited original receipts/protocol evidence are rechecked, never regenerated or retroactively accepted.'}
    write_new(destination/'result.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    args=parser.parse_args()
    report=run_checks(args.registration,args.destination)
    print(json.dumps(report,indent=2))
    return 0 if report['mechanical_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
