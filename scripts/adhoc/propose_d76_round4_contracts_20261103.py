#!/usr/bin/env python3
"""PR #5213: prepare per-candidate source-contract proposals for human review.

2026-11-03. Input: the retained AST inventory JSON. Output: a fresh JSON review
roster; never edits source or supplies runtime exemptions. Native classifications
and protected-function contracts remain explicit pending items until reviewed.
"""
import argparse
import hashlib
import json
from pathlib import Path


GUARDED = {
    'data_sheets_schema.api_runner.RunSpec.base_prompt',
    'data_sheets_schema.api_runner.resolve_prompt',
    'data_sheets_schema.api_runner.build_phase',
    'data_sheets_schema.api_runner.plan',
    'data_sheets_schema.api_runner.execute',
    'data_sheets_schema.native_attribution_registration.registration',
    'data_sheets_schema.native_attribution_registration.write_registration',
}

UNRELATED = {
    'data_sheets_schema.support_judge.render_request':
        'The spec parameter is the already rendered field-specification string, not a RunSpec.',
    'data_sheets_schema.transformation_receipts.validate_spec_against_pair_schema':
        'The spec parameter is a LinkML TransformationSpecification or None, not a generation RunSpec.',
}

# These are review proposals attached to discovered rows, not discovery rules.
# An unknown module remains pending rather than gaining a generic exemption.
HELPER_PRECONDITIONS = {
    'agentic_runtime': 'The rendering caller has validated this RunSpec immediately before deriving installed-agent commands; this helper does not admit a launch.',
    'api_runner': 'A generation or inspection entry has validated this same RunSpec immediately before delegating to this helper; the helper must not serve as a separate launch boundary.',
    'cli.api': 'The CLI constructs each RunSpec from parsed arguments and applies its entry invariant before authority, phase planning or output; callers must not inject an unvalidated mutable spec.',
    'cli.provenance': 'The recorder constructs a fresh spec or restores a literal saved spec, then admits the complete instruction and selected input identities before publication; it accepts no caller-supplied mutable RunSpec.',
    'cli.review': 'The review command delegates to saved-record inspection; any restored RunSpec is literal replay and must never authorize generation.',
    'cli.runs': 'The command inspects a saved request through the literal replay verifier; this route does not authorize execution of the restored RunSpec.',
    'latch_journal': 'For a RunSpec argument, the caller has applied the D76 entry invariant before invoking journal or legacy-evidence helpers; execution ordering and journal admission remain the responsibility of the launch entry.',
    'output_ownership': 'The selected API entry has validated each RunSpec before ownership reads; callers must retain the launch sequence and repeat ownership checks under the existing coordination lock.',
    'receipt_completion': 'The caller is validating a fresh RunSpec during construction, or has applied its entry invariant before receipt authority, input or state access; this helper alone does not authorize provider delivery.',
    'receipts': 'For a RunSpec argument, the generation caller has validated its current binding before reading phase-one snapshot state; snapshot evidence does not itself authorize generation.',
    'removal_repair': 'The API execution caller has validated the RunSpec and established the selected repair/admission context before this helper reads outputs, records state or delivers a repair.',
    'report_claims': 'For a RunSpec argument, the caller has validated its current binding before reading the phase-one snapshot and its pin; this helper is an evidence reader, not a launch entry.',
    'review_pack': 'The review route uses a validated current spec or restores a literal saved spec for inspection only; no resulting instruction or review package authorizes execution.',
    'runs': 'The caller requests inspection of a saved record; this verifier restores a literal replay spec and must not treat that inspection origin as execution authority.',
    'shared_generation': 'The caller is validating a fresh RunSpec during construction, or has applied its entry invariant before shared authority or input access; the public execution/inspection entry owns this precondition.',
    'shared_generation_resources': 'The caller is validating fresh selected specs during construction, or has checked their entry invariants before discovering protected generation resources; discovery is not launch admission.',
    'shared_write_footprint': 'The caller is constructing the RunSpec or has validated it before deriving its output footprint; this helper derives metadata and does not authorize a writer.',
    'snapshot_store': 'For a RunSpec argument, the generation caller has validated the current binding and established the journal/ownership context required for the selected snapshot operation.',
    'source_heading_admission': 'The selected API entry has validated the RunSpec before entering source-heading admission; the caller must preserve the existing registration, journal and owned-output gates.',
    'source_heading_completed': 'For a RunSpec argument, the selected API entry has validated its current binding before completed-capture inspection/publication; read-only form measurement does not establish launch authority.',
    'typed_audit_runtime': 'The selected API execution caller has validated the RunSpec and established its shared audit/admission context before requests, recovery or provider delivery through this helper.',
    'usage_ledger': 'For a RunSpec argument, the generation caller has applied its entry invariant before ledger input/state access; the caller must also preserve the existing journal, lock, ownership and admission sequence.',
}

MEMBER_PRECONDITIONS = {
    'profile_obj': 'The RunSpec is under construction or its caller has validated the current binding before profile lookup; this property is not generation admission.',
    'profile_selection': 'The RunSpec is under construction or its caller has validated the current binding before presenting the selected profile and basis.',
    'header_for_manifest': 'The constructor or validated rendering caller supplies the selected manifest path; this static helper formats metadata without reading inputs or authorizing execution.',
    'is_agentic': 'The caller is constructing the RunSpec or has validated it before route selection; this property only classifies stored fields.',
    'writes_receipt': 'The caller is constructing the RunSpec or has validated it before receipt-route selection; this property only classifies stored fields.',
    'from_render_spec': 'The caller supplies a literal saved renderer specification for inspection; this factory validates/restores it and establishes replay origin, which never authorizes execution.',
    'api_header_values': 'The caller has validated this RunSpec before observing or freezing request settings; recorded replay headers remain literal inspection data.',
    'bind_api_header_values': 'The planning or execution caller has validated this RunSpec before this method reads selected policy/shared authority and binds request settings.',
    'manifest_used': 'The caller is constructing the RunSpec or has validated it before consuming the selected manifest/header declaration; this property only classifies stored fields.',
    'input_identity': 'The planning/execution caller has validated the RunSpec immediately before hashing its selected inputs and shared authority; this method is not an independent admission gate.',
    'render_spec': 'The caller has validated the current RunSpec or is inspecting a genuine literal replay before serializing its rendering selection; serialization never authorizes execution.',
    'instruction': 'Consumers must validate the same RunSpec before using cached instruction text with current inputs; uncached rendering checks the invariant, while the cached text remains inspectable evidence.',
    'output_root': 'The caller is constructing the RunSpec or has validated it before using derived output locations; deriving a path does not authorize writes.',
    'full_path': 'The caller is constructing the RunSpec or has validated it before using the full-output location; deriving a path does not authorize writes.',
    'core_path': 'The caller is constructing the RunSpec or has validated it before using the core-output location; deriving a path does not authorize writes.',
    'report_path': 'The caller is constructing the RunSpec or has validated it before using the report location; deriving a path does not authorize writes.',
    'metadata_dir': 'The caller is constructing the RunSpec or has validated it before using the metadata directory; deriving a path does not authorize writes.',
    'provenance_path': 'The caller is constructing the RunSpec or has validated it before using the provenance location; deriving a path does not authorize writes.',
    'prompt_files': 'The rendering/provenance caller has validated the current RunSpec before enumerating selected prompt assets; this list is not independent input or launch admission.',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or '..' in args.output.parts or args.output.exists() or args.output.is_symlink():
        raise ValueError('fresh absolute output required')
    if args.output.parent.resolve(strict=True) != args.output.parent:
        raise ValueError('physical output parent required')
    inventory = json.loads(args.inventory.read_text())
    rows = []
    for row in inventory['candidates']:
        identity, module, qualname = row['identity'], row['module'], row['qualname']
        short_module = module.removeprefix('data_sheets_schema.')
        mode, precondition = None, None
        pending = None
        if identity in GUARDED:
            mode = 'guarded'
        elif identity in UNRELATED:
            mode, precondition = 'unrelated', UNRELATED[identity]
        elif short_module.startswith('native_'):
            pending = 'independent native factory/helper call-path classification is pending'
        elif qualname.startswith('RunSpec.'):
            precondition = MEMBER_PRECONDITIONS.get(qualname.removeprefix('RunSpec.'))
            mode = 'validated-caller' if precondition else None
        else:
            precondition = HELPER_PRECONDITIONS.get(short_module)
            mode = 'validated-caller' if precondition else None
        if mode is None and pending is None:
            pending = 'unclassified source candidate; no contract may be applied automatically'
        protected = (short_module == 'shared_generation' or
                     identity == 'data_sheets_schema.latch_journal.refuse_legacy_execution')
        rows.append({'identity': identity, 'path': row['path'], 'line': row['line'],
                     'reasons': row['reasons'], 'parameters': row['parameters'],
                     'existing_docstring': row['docstring'], 'proposed_mode': mode,
                     'proposed_precondition': precondition, 'classification_pending': pending,
                     'protected_no_source_edit': protected,
                     'application': 'blocked pending protected-contract ruling' if protected else 'source docstring only, after review'})
    result = {'status': 'proposal only; not source acceptance or runtime proof',
              'inventory': str(args.inventory), 'inventory_sha256': sha(args.inventory),
              'producer_sha256': sha(Path(__file__)),
              'candidate_source_sha256': inventory['candidate_source_sha256'], 'candidates': rows,
              'limits': ['underlying draft discovery has three separately recorded failing-before controls',
                         'native classifications and protected-file handling remain pending',
                         'no source edits are performed by this producer']}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': sha(args.output),
                      'rows': len(rows), 'unclassified': sum(row['classification_pending'] is not None for row in rows),
                      'protected': sum(row['protected_no_source_edit'] for row in rows)}, indent=2))


if __name__ == '__main__':
    main()
