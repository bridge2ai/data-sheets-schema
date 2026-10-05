"""Offline native selection capture and reconstruction from immutable bytes.

Only ``capture`` and ``capture_assets`` read authority files. ``rebuild`` never
falls back to live files, and none of these operations launches a runtime.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
from types import MappingProxyType

from . import native_shared_contract as contract
from . import audit_omissions as omissions
from .profiles import profile_named
from .resources import resource_path
from .schema_snapshot import capture_schema
from .schema_view import captured_view

PROMPT = 'src/download/prompts/d4d_generic_arm_prompt_v10.md'
COMMON_POLICY = 'src/download/prompts/shared_generation_v1.md'
POLICY = 'src/download/prompts/native_shared_generation_v1.md'
RECEIPT_POLICY = 'src/download/prompts/native_shared_receipt_policy_v1.md'
RECEIPT_POLICY_SHA256 = 'de90df8ec7818b645e352fbae6bcc153387c02d7fcf71ef8f2abe409a083b75a'
ATTRIBUTION_POLICY = 'src/download/prompts/native_source_attribution_v1.md'
GUARD = '.claude/agents/d4d-provenance-guard-v2.md'
OMISSION_PREFIX = 'src/data_sheets_schema/omission_inventory_v1/'
ASSET_HASHES = MappingProxyType({
    '.claude/agents/d4d-provenance-guard-v2.md': '10dc4689e1855096ef3507de01b129abfd5795690fbcfbd3458407741fe30085',
    '.claude/commands/d4d-agent-v2.md': 'dcb33659014a68596a248ed768c196dd0b1e396a0fe41579918dff95ac559299',
    '.claude/commands/d4d-full-core-v2.md': '2f52d3e70d7a6f3098b7acfcc80b9e9d0f318c9ca1517f711eae9fb789410124',
    '.claude/commands/d4d-uniform-rules-v2.md': '7b511b1ef15d6fb56d47dc58b367196ed9c7269a61406ed19127481f719c885a',
    'src/data_sheets_schema/omission_inventory_v1/context.schema.json': '4cb51a481905d272d24726dddd22ab91ed3e3ce1e6a23f37d50d2f1cefa9c2c8',
    'src/data_sheets_schema/omission_inventory_v1/policy.md': '0b197cf8bafe1f3df53f3c23922e9e38d514cca42979b90282022b8bef4c0b0d',
    'src/data_sheets_schema/omission_inventory_v1/response.schema.json': '90d9e0fcb50b391c9345b0150af2a43f7c3581673b89f35069a70f57046e6d07',
    'src/download/prompts/d4d_generic_arm_prompt_v10.md': 'a3a2004cef2147b3351613cb38a67abde1d58c91c19ee0c72c66ff476d0722ec',
    'src/download/prompts/evidence_protocol_v7.md': '72039b09bfaaa43d683c7a0ba7560aace0d5c19209f7a1e1c70c4290ee48ddb6',
    'src/download/prompts/native_shared_generation_v1.md': 'ff679e9a6a76a760e57d7c0e6df88102fe630a6b802b513dc0b0144aa39ac18c',
    'src/download/prompts/native_shared_receipt_policy_v1.md': RECEIPT_POLICY_SHA256,
    'src/download/prompts/native_source_attribution_v1.md': 'e13f0bd8de8e4e28cd1c1216799defb7005f7e041698698a4478d824e8acc761',
    'src/download/prompts/shared_generation_v1.md': '34608f26b4a0407da036486a6e8ec6692df6b54594335140bdc3df4229d78450',
})
_PLAYBOOK_REF = re.compile(r'\.claude/(?:commands|agents)/[\w.-]+\.md')


def descriptor() -> dict:
    """Derived protocol identity, with no invented descriptor file path."""
    return {'protocol': contract.NAME, 'version': contract.VERSION,
            'condition': contract.CONDITION, 'renderer': contract.RENDERER,
            'runtime': contract.RUNTIME, 'native_shared_generation_version': 1,
            'native_source_attribution_version': 0, 'shared_generation_version': 0,
            'api_playbook_version': 0, 'receipt_completion_version': 0,
            'removal_repair_version': 0, 'typed_protocol': 'typed_audit_protocol_v1',
            'projection': 'native_shared_source_projection_v1',
            'receipt_policy': {'path': RECEIPT_POLICY, 'sha256': RECEIPT_POLICY_SHA256},
            'assets': dict(ASSET_HASHES)}


def descriptor_capture() -> contract.DescriptorCapture:
    raw = contract.canonical(descriptor())
    return contract.DescriptorCapture(raw, contract.sha(raw))


def _asset_bytes(authority) -> dict:
    result = {}
    for artifact in authority:
        if artifact.pin.role.startswith('asset:'):
            name = artifact.pin.role[len('asset:'):]
            if name in result:
                raise ValueError('duplicate selected asset role')
            result[name] = artifact.raw
    if set(result) != set(ASSET_HASHES):
        raise ValueError('selected native asset closure differs from the fixed protocol')
    for name, raw in result.items():
        if contract.sha(raw) != ASSET_HASHES[name]:
            raise ValueError('selected native asset bytes changed: ' + name)
        raw.decode('utf-8')
    reached, pending = set(), [PROMPT]
    while pending:
        name = pending.pop()
        for ref in _PLAYBOOK_REF.findall(result[name].decode('utf-8')):
            if ref not in result:
                raise ValueError('selected parent references an uncaptured playbook')
            if ref not in reached:
                reached.add(ref)
                pending.append(ref)
    if reached != {name for name in ASSET_HASHES if name.startswith('.claude/')}:
        raise ValueError('selected parent transitive playbook closure differs')
    return result


def _body(raw: bytes) -> str:
    text = raw.decode('utf-8')
    if text.count('## Prompt body') != 1:
        raise ValueError('selected policy has no unique prompt body')
    return text.split('## Prompt body', 1)[1].strip()


def projected_rules(selection: contract.NativeSelectionCapture) -> str:
    return rules_from_assets(selection.authority)


def rules_from_assets(authority: tuple[contract.CapturedArtifact, ...]) -> str:
    """Select pinned factual rules; replace the parent's execution procedure.

    Parent playbooks remain provenance inputs, not a second set of executable
    instructions. The common v10 rules are included once, including role review.
    """
    assets = _asset_bytes(authority)
    parent = _body(assets[PROMPT])
    start = 'UNIFORM DECISION RULES — these apply identically to every project and every arm:'
    end = '## Shared generation rules v1'
    if parent.count(start) != 1 or parent.count(end) != 1 or parent.index(start) >= parent.index(end):
        raise ValueError('native projection cannot adapt changed parent sections')
    rules = parent[parent.index(start):parent.index(end)].strip()
    guard = assets[GUARD].decode('utf-8')
    first, last = '## Governing Rule', '## Allowed Inputs By Phase'
    if guard.count(first) != 1 or guard.count(last) != 1:
        raise ValueError('native projection cannot adapt changed guard sections')
    # The captured manifest is supplied explicitly; never prescribe the
    # historical default manifest as a second authority.
    factual = guard[guard.index(first):guard.index(last)].strip().replace(
        '`data/preprocessed/source_manifest.yaml`', 'captured source manifest')
    return '\n\n'.join((factual, rules, _body(assets[COMMON_POLICY]),
                          _body(assets[POLICY]), _body(assets[RECEIPT_POLICY]),
                          _body(assets[ATTRIBUTION_POLICY]))) + '\n'


def _pin(artifact) -> dict:
    return {key: getattr(artifact.pin, key) for key in ('path', 'bytes', 'sha256')}


def _artifact(role, path, raw):
    return contract.CapturedArtifact(
        contract.ArtifactPin(role, str(path), len(raw), contract.sha(raw)), raw)


def _declarations(doc):
    yield 'receipt_policy', doc['receipt_policy']
    for name, pin in sorted(doc['selection']['assets'].items()):
        yield 'asset:' + name, pin
    for name in ('bundle', 'chunk_manifest', 'context', 'source_manifest'):
        if doc['inputs'][name] is not None:
            yield name, doc['inputs'][name]
    vocabulary = doc['inputs']['profile']['vocabulary']
    if vocabulary is not None:
        yield 'vocabulary', vocabulary
    for kind in ('full_schema', 'core_schema'):
        for index, source in enumerate(doc['inputs'][kind]['sources']):
            yield f'{kind}:{index}', {k: source[k] for k in ('path', 'bytes', 'sha256')}


def _declared_schemas(doc, artifacts):
    """Package declared bytes for rebuild; this does not validate the graph."""
    result = []
    for kind, cls in (('full', 'Dataset'), ('core', 'CoreDataset')):
        declaration = doc['inputs'][kind + '_schema']
        sources = tuple(artifacts[f'{kind}_schema:{i}'] for i in range(len(declaration['sources'])))
        rows = tuple((source['name'], artifact.pin.role)
                     for source, artifact in zip(declaration['sources'], sources))
        result.append(contract.SchemaClosureCapture(
            contract.schema_closure_sha(sources, rows), rows, kind, cls,
            declaration['sources'][0]['name'], sources))
    return tuple(result)


def _schemas(doc, artifacts):
    result = []
    for kind, cls in (('full', 'Dataset'), ('core', 'CoreDataset')):
        declaration = doc['inputs'][kind + '_schema']
        sources = tuple(artifacts[f'{kind}_schema:{i}'] for i in range(len(declaration['sources'])))
        rows = tuple((source['name'], artifact.pin.role)
                     for source, artifact in zip(declaration['sources'], sources))
        frozen = {Path(a.pin.path): a.raw for a in sources}

        def read(path):
            if path not in frozen:
                raise ValueError('selected schema import is outside the complete captured closure')
            return frozen[path]

        for artifact in sources:
            omissions._mapping(artifact.raw, 'native schema', limit=contract.HARD_LIMITS['schema_member_bytes'])
        snapshot = capture_schema(Path(declaration['root']), read_bytes=read,
                                  strict=True, logical_paths=True)
        actual = [(str(name), str(path), raw) for name, path, raw in snapshot.sources]
        expected = [(row['name'], a.pin.path, a.raw) for row, a in zip(declaration['sources'], sources)]
        if actual != expected:
            raise ValueError('native schema names, order or import closure differ')
        with captured_view(snapshot) as view:
            if view.get_class(cls) is None:
                raise ValueError('native captured schema lacks ' + cls)
        result.append(contract.SchemaClosureCapture(
            contract.schema_closure_sha(sources, rows), rows, kind, cls,
            declaration['sources'][0]['name'], sources))
    return tuple(result)


def rebuild(registration: contract.CapturedArtifact,
            authority: tuple[contract.CapturedArtifact, ...],
            schemas: tuple[contract.SchemaClosureCapture, ...],
            receipt_policy: contract.CapturedArtifact) -> contract.NativeSelectionCapture:
    """Independently reconstruct S from complete bytes; no live fallback."""
    if (type(registration) is not contract.CapturedArtifact
            or type(receipt_policy) is not contract.CapturedArtifact
            or type(authority) is not tuple or type(schemas) is not tuple
            or any(type(a) is not contract.CapturedArtifact for a in authority)
            or any(type(s) is not contract.SchemaClosureCapture for s in schemas)):
        raise ValueError('native selection requires immutable captured carriers')
    doc = contract.parse_selection(registration.raw)
    expected_descriptor = descriptor_capture()
    if doc['selection']['descriptor_sha256'] != expected_descriptor.sha256:
        raise ValueError('native selection descriptor differs from the fixed implementation')
    if set(doc['selection']['assets']) != set(ASSET_HASHES):
        raise ValueError('native selection does not declare the complete selected assets')
    artifacts = (receipt_policy, *authority, *(a for s in schemas for a in s.sources))
    by_role = {a.pin.role: a for a in artifacts}
    declarations = dict(_declarations(doc))
    if len(by_role) != len(artifacts) or set(by_role) != set(declarations):
        raise ValueError('captured authority has missing, extra or duplicate roles')
    by_path = {}
    for role, pin in declarations.items():
        observed = by_role[role]
        if _pin(observed) != pin:
            raise ValueError('captured authority differs from selected identity: ' + role)
        if pin['path'] in by_path and by_path[pin['path']] != observed.raw:
            raise ValueError('same authority path has different captured bytes')
        by_path[pin['path']] = observed.raw
    assets = _asset_bytes(authority)
    selected_profile = doc['inputs']['profile']
    profile = profile_named(selected_profile['name'])
    if (profile.vocabulary_pin is None) != (selected_profile['vocabulary'] is None):
        raise ValueError('native profile requires its declared vocabulary without fallback')
    for role in ('bundle', 'chunk_manifest', 'source_manifest', 'vocabulary'):
        if role in by_role:
            by_role[role].raw.decode('utf-8')
    context = contract.strict_json(by_role['context'].raw, 'generation context', doc['bounds']['max_input_bytes'])
    context_schema = contract.strict_json(assets[OMISSION_PREFIX + 'context.schema.json'])
    if omissions._shape(context, context_schema):
        raise ValueError('native generation context must satisfy omission_context_v1')
    owners = [scope['owner'] for scope in context['scopes']]
    if owners.count('') != 1 or len(owners) != len(set(owners)):
        raise ValueError('native generation context requires exactly one root and unique owners')
    contract.parse_receipt_policy(receipt_policy.raw, RECEIPT_POLICY_SHA256)
    reconstructed = _schemas(doc, by_role)
    if schemas != reconstructed:
        raise ValueError('saved native schema carriers differ from complete reconstruction')
    return contract.NativeSelectionCapture(
        arm=doc['run']['arm'], authority=authority,
        bounds_json=contract.canonical(doc['bounds']), condition=contract.CONDITION,
        descriptor=expected_descriptor, project=doc['run']['project'],
        protocol=contract.NAME, receipt_policy=receipt_policy, registration=registration,
        roles=contract.role_paths(doc['registration_path'], doc['stage_root']),
        run_id=doc['registration_id'], schemas=reconstructed)


def _metadata(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _canonical_file(path):
    path = Path(contract.canonical_path(str(path)))
    if path.resolve(strict=False) != path:
        raise ValueError('native authority or stage path uses a filesystem alias')
    return path


class _Reads:
    def __init__(self, limit):
        self.limit, self.total = limit, 0
        self.files, self.identities, self.inodes = {}, {}, {}

    def read(self, path, maximum):
        path = _canonical_file(path)
        if path in self.files:
            raw = self.files[path]
            if len(raw) > maximum:
                raise ValueError('shared authority exceeds its role-specific byte bound')
            return raw
        if len(self.files) >= contract.HARD_LIMITS['authority_files']:
            raise ValueError('native authority exceeds its file-count bound')
        maximum = min(maximum, self.limit - self.total)
        if maximum < 1:
            raise ValueError('native authority exceeds its aggregate byte bound')
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('native authority must be an unaliased regular file')
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if _metadata(opened) != _metadata(before) or opened.st_size > maximum:
                raise ValueError('native authority changed or exceeds its byte bound')
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        if (not raw or len(raw) > maximum or len(raw) != opened.st_size
                or _metadata(after) != _metadata(before) or _metadata(path.lstat()) != _metadata(before)):
            raise ValueError('native authority changed during bounded capture')
        _canonical_file(path)
        inode = (before.st_dev, before.st_ino)
        if inode in self.inodes and self.inodes[inode] != path:
            raise ValueError('native authority paths alias the same file')
        self.inodes[inode] = path
        self.identities[path] = _metadata(before)
        self.files[path] = raw
        self.total += len(raw)
        return raw

    def stable(self):
        for path, expected in self.identities.items():
            if _metadata(_canonical_file(path).lstat()) != expected:
                raise ValueError('native authority changed before capture completed')


def _asset_path(name):
    # Omission readers use their module-adjacent files, rather than cwd
    # resource overrides. Bind the same actual source at this boundary.
    if name.startswith(OMISSION_PREFIX):
        return omissions.ASSETS / name[len(OMISSION_PREFIX):]
    return resource_path(name).absolute()


def capture_assets() -> tuple[contract.CapturedArtifact, ...]:
    reader = _Reads(contract.HARD_LIMITS['authority_raw_total_bytes'])
    assets = tuple(_artifact('asset:' + name, _asset_path(name), reader.read(
        _asset_path(name), contract.HARD_LIMITS['input_bytes'])) for name in sorted(ASSET_HASHES))
    _asset_bytes(assets)
    reader.stable()
    return assets


def capture(selection_path: str | Path) -> contract.NativeSelectionCapture:
    """Capture current real S and its closed authority before preparation."""
    path = _canonical_file(selection_path)
    reader = _Reads(contract.HARD_LIMITS['authority_raw_total_bytes'])
    raw = reader.read(path, contract.HARD_LIMITS['selection_metadata_bytes'])
    doc = contract.parse_selection(raw)
    if doc['registration_path'] != str(path):
        raise ValueError('native registration was read from a different path')
    reader.limit = doc['bounds']['max_authority_bytes']
    stage_root = _canonical_file(doc['stage_root'])
    if stage_root.exists() and not stage_root.is_dir():
        raise ValueError('native stage root is not a directory')
    if set(doc['selection']['assets']) != set(ASSET_HASHES):
        raise ValueError('native asset declaration differs from its selected closure')
    for name, pin in doc['selection']['assets'].items():
        if pin['path'] != str(_canonical_file(_asset_path(name))):
            raise ValueError('native asset pin names a different installed resource')
    from . import api_runner
    for key, installed in (('full_schema', api_runner.FULL_SCHEMA_PATH),
                           ('core_schema', api_runner.CORE_SCHEMA_PATH)):
        if doc['inputs'][key]['root'] != str(_canonical_file(resource_path(installed).absolute())):
            raise ValueError('native schema is not the actual selected validation/digest root')
    profile = profile_named(doc['inputs']['profile']['name'])
    vocabulary = doc['inputs']['profile']['vocabulary']
    actual_vocab = profile.pin_path
    if ((None if actual_vocab is None else str(_canonical_file(actual_vocab.absolute())))
            != (None if vocabulary is None else vocabulary['path'])):
        raise ValueError('native vocabulary differs from the selected profile resource')
    artifacts = {}
    for role, pin in _declarations(doc):
        maximum = doc['bounds']['max_input_bytes'] if role in {
            'bundle', 'chunk_manifest', 'context', 'source_manifest', 'vocabulary'} else contract.HARD_LIMITS['schema_member_bytes']
        data = reader.read(pin['path'], min(maximum, pin['bytes']))
        artifacts[role] = _artifact(role, pin['path'], data)
        if _pin(artifacts[role]) != pin:
            raise ValueError('native authority bytes differ from their registration: ' + role)
    schemas = _declared_schemas(doc, artifacts)
    authority = tuple(a for role, a in artifacts.items()
                      if role != 'receipt_policy' and not role.startswith(('full_schema:', 'core_schema:')))
    result = rebuild(_artifact('selection', path, raw), authority, schemas, artifacts['receipt_policy'])
    reader.stable()
    if _canonical_file(stage_root) != stage_root:
        raise ValueError('native stage root changed during capture')
    return result
