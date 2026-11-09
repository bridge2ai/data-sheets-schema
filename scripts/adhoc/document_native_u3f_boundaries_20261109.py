"""U3-F D76 source declarations, 2026-11-09.

Inputs: explicitly reviewed boundary/precondition roster below. Outputs: source
docstrings only; protected sidecar remains an owner packet. Local U3-F handoff.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = {
 'backfill_checks.compute': 'Caller supplies recorded provenance, not a live RunSpec; native receipts reconstruct the explicitly recorded selection through block_for.',
 'cli.prompt.render_native_shared': 'CLI supplies explicit selection/runtime paths to v2 prepare, which constructs and guards its RunSpec before instruction access; this command grants no execution authority.',
 'cli.provenance.backfill_checks': 'CLI supplies recorded provenance to compute; native receipt reconstruction validates its recorded selection rather than accepting a caller RunSpec.',
 'cli.receipts.check': 'CLI supplies explicit recorded or native selection paths; native receipt helpers reconstruct the admitted selection before assessing receipts.',
 'native_execution_orchestration.authorizations': 'Caller supplies execution bytes and a fixed contract; verified reconstructs the selected preparation before external authorization comparisons.',
 'native_execution_orchestration.launch': 'Caller supplies explicit execution registration and fixed effects; registration.verified reconstructs the guarded preparation before any execution effect.',
 'native_execution_registration_v2.prepare': 'Caller supplies explicit selection and runtime paths, never a RunSpec argument; this factory constructs RunSpec and calls _require_registered_input_spellings before instruction, input_identity or render_spec access.',
 'native_execution_registration_v2.verify_preparer': 'Caller supplies bounded preparation bytes and job identity; prepare reconstructs and guards the fresh RunSpec before the full comparison.',
 'native_execution_registration_v2.verified': 'Caller supplies execution bytes and an explicit classifier projection; verification rederives preparation through verify_preparer before consumer reconstruction.',
 'native_execution_registration_v2.admit': 'Caller supplies explicit authorization paths and classifier projection; verified rederives the guarded preparation before admission checks.',
 'native_shared_attribution.saved': 'Caller supplies an independently verified spec and canonical preparation/composition plus actual captured instruction; saved replay does not confer admission.',
 'native_shared_attribution_orchestration.live': 'Caller supplies a verified spec from the same preparation/composition; reconstruct_composition rechecks that preparation and compares render_spec before observation.',
 'native_shared_callback_capture.FrozenSpec.capture': 'Admission caller supplies the unchanged validated RunSpec from freshly verified preparation; this captures fields and render_spec without granting authority.',
 'native_shared_callback_orchestration.preloaded_callbacks': 'Main-thread caller has just verified outer execution through A and supplies its unchanged prepared spec and composition; frozen capture is not independent admission.',
 'native_shared_capture_orchestration.activate': 'Fixed lifetime supplies selected execution bytes; registration.verified and reconstruct_composition rederive preparation before activation effects.',
 'native_shared_capture_orchestration.initialize': 'Caller supplies actual observed initialization; _base reconstructs the active execution and its guarded preparation before stream binding.',
 'native_shared_capture_orchestration.capture_stage': 'Caller supplies the selected registration path; _load_live reconstructs active execution and preparation before returning the pending invocation.',
 'native_shared_capture_orchestration.publish_stage': 'Caller supplies a captured invocation; capture_stage rechecks its live execution and guarded preparation before publication.',
 'native_shared_capture_orchestration.selected_receipt_paths': 'Caller supplies explicit active selection; _base reconstructs the execution and its guarded preparation before returning paths.',
 'native_shared_capture_orchestration.live_receipt_block': 'Caller supplies explicit active selection and output paths; _load_live reconstructs the selected preparation before receipt assessment.',
 'native_shared_capture_orchestration.live_provenance_block': 'Caller supplies explicit active selection; _load_live reconstructs preparation and current final obligations before provenance assessment.',
 'native_shared_capture_orchestration.recorded_receipt_block': 'Caller supplies a validated spec or None plus explicit recorded provenance; _recorded_run reconstructs the recorded selection and compares render_spec before assessment.',
 'native_shared_capture_orchestration.recorded_receipt_claims': 'Caller supplies a validated spec or None and a checked receipt block; _recorded_run reconstructs selection and compares the recorded render_spec before deriving claims.',
 'native_shared_controller.reconstruct_composition': 'Caller supplies the unchanged validated spec and independently verified preparation, selection and runtime; compose compares the complete captured composition without live reconstruction.',
 'native_shared_controller.verified_composition': 'Caller supplies the unchanged validated spec and independently verified reconstruction inputs; reconstruct_composition compares the complete composition.',
 'native_shared_controller_orchestration.compose': 'Caller supplies explicit preparation bytes and instruction path; _compose verifies preparation and reconstructs the guarded RunSpec before composing.',
 'native_shared_controller_orchestration.reconstruct_composition': 'Caller supplies composition bytes; _compose revalidates preparation and reconstructs its RunSpec before comparing the complete composition.',
 'native_shared_controller_orchestration.verified_composition': 'Caller supplies composition bytes; reconstruct_composition performs fresh preparation and RunSpec reconstruction before comparison.',
 'native_shared_controller_orchestration.CallbackAdapter.activate_before_dispatch': 'Adapter holds the validated spec from composition reconstruction; fresh execution verification precedes freezing the same spec for callback admission.',
 'native_shared_execution_orchestration.authorizations': 'Caller supplies execution bytes and a fixed verified value; the common authorization routine freshly verifies preparation before checking declarations.',
 'native_shared_execution_orchestration.launch': 'Caller supplies explicit execution registration; registration.verified reconstructs guarded preparation before creating fixed effects or dispatching.',
 'native_shared_registration.permission_expectation': 'Caller supplies the unchanged validated spec from verified composition and its selected runtime; expected probe bindings grant no execution authority.',
 'native_shared_registration.rebuild_v2_body': 'A has verified preparation and supplies an explicit classifier projection; input-only reconstruction verifies composition and its prepared spec before producing the body.',
 'native_shared_registration_orchestration.registration': 'Caller supplies explicit composition/system paths; _registration_body verifies preparation and composition before creating an execution proposal.',
 'native_shared_registration_orchestration.verified_v2_body': 'Caller supplies bounded body/preparation bytes; _registration_body reconstructs guarded preparation and compares the complete body.',
 'native_shared_registration_orchestration.verified': 'Caller supplies outer execution bytes; execution_v2.verified freshly rederives guarded preparation under verified controls.',
 'native_shared_results.rebuild': 'Caller supplies bounded captured pool and execution value; RunSpec.from_render_spec validates the captured spec before replay, with no filesystem reads or live admission.',
 'native_shared_results_orchestration.capture': 'Caller supplies verified execution and complete controls; _load reconstructs selected preparation before bounded capture and saved replay.',
 'native_shared_results_orchestration.prepare': 'Caller supplies captured pool, verified execution and complete controls; rebuild validates the captured render spec before result assessment.',
 'native_shared_results_orchestration.require_saved_basis': 'Common reader has checked retained report bytes; saved reconstruction validates the captured render spec and never upgrades failed attempts to success.',
 'native_shared_stage.__main__.main': 'CLI supplies an explicit registration path; capture_stage revalidates selected preparation and pending invocation before replay and publication.',
 'receipts.block_for': 'Caller supplies a validated snapshot_spec when present or explicit recorded input authority; native receipt helpers reconstruct and compare selected preparation before native assessment.',
}

def main():
    grouped = {}
    for identity, precondition in CONTRACTS.items():
        parts = identity.split('.')
        for end in range(len(parts)-1, 0, -1):
            path = ROOT / 'src/data_sheets_schema' / ('/'.join(parts[:end])+'.py')
            if path.is_file():
                grouped.setdefault(path, []).append(('.'.join(parts[end:]), precondition))
                break
        else:
            raise ValueError(identity)
    for path, rows in grouped.items():
        source = path.read_text()
        tree = ast.parse(source)
        edits = []
        lines = source.splitlines(keepends=True)
        for qualname, precondition in rows:
            body = tree.body
            for name in qualname.split('.'):
                matches = [n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name]
                assert len(matches) == 1, (path, qualname)
                node = matches[0]
                body = node.body
            doc = ast.get_docstring(node, clean=False) or ''
            doc = doc.replace('    RunSpec boundary: guarded\n', '')
            assert 'RunSpec boundary:' not in doc
            indent = ' ' * (node.col_offset+4)
            block = '\n\n' + indent + 'RunSpec boundary: validated-caller\n\n' + indent + 'RunSpec precondition: ' + precondition + '\n' + indent
            if ast.get_docstring(node, clean=False) is not None:
                first = node.body[0]
                start, end = first.lineno-1, first.end_lineno
                old = ''.join(lines[start:end])
                position = old.rfind('"""')
                assert position >= 0
                old = old.replace('    RunSpec boundary: guarded\n', '')
                position = old.rfind('"""')
                replacement = old[:position].rstrip() + block + old[position:]
            else:
                start = end = node.body[0].lineno-1
                replacement = indent+'"""'+block.lstrip('\n')+'"""\n'
            edits.append((start, end, replacement))
        for start, end, replacement in sorted(edits, reverse=True):
            lines[start:end] = [replacement]
        updated = ''.join(lines)
        ast.parse(updated)
        path.write_text(updated)

if __name__ == '__main__':
    main()
