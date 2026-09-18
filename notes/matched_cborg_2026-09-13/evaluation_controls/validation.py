"""Exact-file validators for native semantic and field-agent ratings."""
import argparse
import contextlib
import io
import json
from pathlib import Path

from registration import BudgetStop, read_json, sha


def validator_argv(manifest, job):
    argv = [manifest['python'], str(Path(__file__).resolve()), '--candidate', job['candidate'],
        '--input', job['input'], '--definition', job['agent_definition'], '--context', job['context_path'],
        '--rubric', job['rubric'], '--style', job['style'], '--project', job['project'],
        '--method', job['method'], '--model', manifest['model']['model'],
        '--rubric-file', job['rubric_file'], '--schema-dir', manifest['prompts_dir']]
    return argv


def validate_native(path, job, manifest):
    document = read_json(path)
    if not isinstance(document, dict):
        raise BudgetStop('native evaluation must be one JSON object')
    if job['style'] == 'semantic_agent':
        from data_sheets_schema.evaluation.validate import validate_outputs
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = validate_outputs([Path(path)], rubric=job['rubric'],
                schema_dir=Path(manifest['prompts_dir']), input_path=Path(job['input']),
                definition_path=Path(job['agent_definition']), context_path=Path(job['context_path']))
        if status:
            raise BudgetStop('semantic evaluation failed its exact-file instrument validator: ' + output.getvalue())
        metadata = document.get('metadata', {})
        for key, value in (('project', job['project']), ('method', job['method']), ('d4d_file', job['input'])):
            if document.get(key) != value:
                raise BudgetStop('semantic output does not identify registered ' + key)
        if metadata.get('rubric_sha256') != sha(job['rubric_file']):
            raise BudgetStop('semantic output differs from the registered source rubric')
        if metadata.get('instrument_kind') != 'agent_definition':
            raise BudgetStop('native semantic output does not name its definition instrument')
        report = {'valid': True, 'style': job['style'], 'rubric': job['rubric']}
    elif job['style'] == 'field_agent':
        from data_sheets_schema.field_agent_contract import validate_output
        report = validate_output(Path(path), rubric=job['rubric'], project=job['project'],
            method=job['method'], input_path=Path(job['input']), definition_path=Path(job['agent_definition']),
            context_path=Path(job['context_path']))
    else:
        raise BudgetStop('unknown native evaluation style')
    if document.get('d4d_file') != job['input']:
        raise BudgetStop('native evaluation does not identify the registered input filename')
    if document.get('metadata', {}).get('rubric_sha256') != sha(job['rubric_file']):
        raise BudgetStop('native evaluation differs from the selected source rubric')
    model = document.get('model', {})
    evaluation_types = {'llm_as_judge', 'semantic_llm_judge'} if job['style'] == 'semantic_agent' else {'llm_as_judge'}
    if (model.get('name') != manifest['model']['model'] or
        model.get('evaluation_type') not in evaluation_types or
        model.get('evaluator_model', manifest['model']['model']) != manifest['model']['model']):
        raise BudgetStop('native evaluation output names a different model')
    return {'passed': True, 'validator': report, 'candidate_sha256': sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('candidate', 'input', 'definition', 'context', 'rubric', 'style', 'project',
                   'method', 'model', 'rubric-file', 'schema-dir'):
        parser.add_argument('--' + option, required=True)
    args = vars(parser.parse_args())
    job = {**args, 'agent_definition': args['definition'], 'context_path': args['context']}
    manifest = {'model': {'model': args['model']}, 'prompts_dir': args['schema_dir']}
    try:
        report = validate_native(Path(args['candidate']), job, manifest)
    except (OSError, ValueError, ImportError, BudgetStop) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
