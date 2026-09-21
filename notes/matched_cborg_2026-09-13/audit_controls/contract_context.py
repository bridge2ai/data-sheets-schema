"""Opt-in persistent copies of the unchanged shared Phase 3 contract (#2164)."""
from pathlib import Path

from budgeted_cborg import BudgetStop

KEY = 'audit_contract_context'
KIND = 'persistent_protocol_v1'


def configuration(manifest):
    """Absence preserves historical behavior; any present selector is strict."""
    if KEY not in manifest:
        return None
    block = manifest[KEY]
    from .registration import scientific_contract
    scientific_contract(manifest)
    if (type(block) is not dict or block != {'kind': KIND} or
            manifest.get('kind') != 'd4d_native_audit_continuation'):
        raise BudgetStop('persistent audit contract requires an audit-only persistent_protocol_v1 selector '
                         'with a registered scientific contract')
    return block


def enabled(manifest):
    return configuration(manifest) is not None


def select(manifest, value):
    if type(value) is not bool:
        raise BudgetStop('persistent audit contract requires an explicit boolean')
    if value:
        manifest[KEY] = {'kind': KIND}


def render_system(manifest, original):
    """Append exact registered protocol bytes and the shared audit contract.

    Full inherited identity and pin verification remain registration checks.
    Preparation renders before its new pin map exists, so this renderer checks
    the existing canonical file and readable-input identity without repinning it.
    """
    if not enabled(manifest):
        return original
    try:
        value = manifest['inputs']['protocol']
        readable = manifest['job']['readable_inputs']
        if not isinstance(value, str) or not value or not isinstance(readable, list) or value not in readable:
            raise ValueError('protocol is not a registered readable input')
        path = Path(value)
        if not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink() or not path.is_file():
            raise ValueError('protocol is not a canonical file')
        # read_text() would normalize CRLF. Round-tripping strict UTF-8 keeps
        # the exact existing protocol bytes inside the rendered system prompt.
        protocol = path.read_bytes().decode('utf-8')
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise BudgetStop('persistent audit contract requires the exact readable protocol file') from error
    from data_sheets_schema.api_runner import evidence_phase_contract
    version = manifest['render_version']
    audit = evidence_phase_contract('audit', version)
    return (original + '\nPersistent shared audit contract\n'
            'The following protocol and Phase 3 text reproduce the registered shared contract.\n'
            'The input/artifact names original_full and original_core identify frozen record states. '
            'They are distinct from findings[].record, whose values are full, core or both. '
            'source_review is bound to the original_full inventory as specified below.\n\n'
            'Registered evidence protocol (verbatim)\n' + protocol
            + f'\n\nShared Phase 3 audit contract (renderer {version}, verbatim)\n' + audit + '\n')
