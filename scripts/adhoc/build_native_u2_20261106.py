# Purpose: generate additive v2 source copies for #5508. Inputs: frozen v1 files.
# Outputs: versioned preparers/consumers; no v1 edits. Date: 2026-11-06.
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def copy(source, target, substitutions):
    text = (ROOT/source).read_text()
    for old, new in substitutions:
        assert old in text, old
        text = text.replace(old, new)
    (ROOT/target).write_text(text)

base = 'notes/matched_cborg_2026-09-13/'
copy(base+'prepare_registration.py', base+'prepare_registration_v2.py', [
    ('DEFAULT_CANARY_ORDER = "CHORUS_api_rep1,CHORUS_agentic_rep1,KIDS_FIRST_api_rep1,KIDS_FIRST_agentic_rep1"\nPROJECTS = ["CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]\n', ''),
    ('parser.add_argument("--canary-order", default=DEFAULT_CANARY_ORDER,', 'parser.add_argument("--projects", required=True, help="Comma-separated registry project identifiers")\n    parser.add_argument("--canary-order", required=True,'),
    ('"the API-first default; a native-first sequence names the agentic job first."', '"their saved order; new registrations must select an explicit sequence."'),
    ('"canary": replicate == 1 and case["project"] in {"CHORUS", "KIDS_FIRST"},', '"canary": identifier in {name.strip() for name in args.canary_order.split(",")},'),
    ('if sorted(canary_order) != sorted(DEFAULT_CANARY_ORDER.split(",")):\n        parser.error("canary order must name exactly the four registered canaries once each")', 'if not canary_order or len(set(canary_order)) != len(canary_order):\n        parser.error("canary order must name unique job identifiers")\n    projects = [name.strip() for name in args.projects.split(",") if name.strip()]\n    if not projects or len(set(projects)) != len(projects):\n        parser.error("projects must name unique registry identifiers")'),
    ('cases = [{"project": p,', 'if any(not registry.declares(p) for p in projects):\n        parser.error("every project must be declared by the source registry")\n    cases = [{"project": p,'),
    ('for p in PROJECTS]', 'for p in projects]'),
    ('pins = {}\n', 'available = {f"{case[\'project\']}_{arm}_rep{rep}" for case in cases\n                 for arm in ("api", "agentic") for rep in range(1, case["replicates"] + 1)}\n    if not set(canary_order) <= available:\n        parser.error("canary order names jobs outside the selected registered roster")\n    pins = {}\n'),
    ('"required_canaries": 4', '"required_canaries": len(canary_order)'),
])
copy('notes/claudecode_direct/prepare_direct.py', 'notes/claudecode_direct/prepare_direct_v2.py', [
    ('parser.add_argument("--project", default="CHORUS")', 'parser.add_argument("--project", required=True)'),
    ('HERE / "prepare_direct.py",', 'Path(__file__),'),
])
pkg = 'src/data_sheets_schema/'
copy(pkg+'native_attribution_registration.py', pkg+'native_attribution_registration_v2.py', [
    ('SCHEMA_VERSION = 1', 'SCHEMA_VERSION = 2'),
    ("'checker_source_tree_sha256': _code_pins(),", "'controller_authority': _controller_authority(),\n              'checker_source_tree_sha256': _code_pins(),"),
    ('def registration(spec):', '''def _controller_authority():
    from data_sheets_schema import native_attribution_controller_v2 as controller
    return {'version': 2, 'manifest': str(controller.SOURCES_PATH),
            'sha256': controller.SOURCES_SHA256, 'sources': controller.controller_sources()}


def registration(spec):'''),
])
copy(pkg+'native_attribution_controller.py', pkg+'native_attribution_controller_v2.py', [
    ('native_attribution_registration as draft', 'native_attribution_registration_v2 as draft'),
    ('VERSION = 1', 'VERSION = 2'),
    ('native_controller_sources_v1.json', 'native_controller_sources_v2.json'),
    ('e55f332b2cc4d679c2ffa9cba5d40acb8a333fd821e3b6d0f2746b8cba7f3971', 'V2_MANIFEST_DIGEST_PENDING'),
    ("manifest = draft._json(raw)\n", "manifest = draft._json(raw)\n    if type(manifest.get('version')) is not int or manifest['version'] != 2:\n        raise ValueError('v2 controller requires v2 source authority')\n"),
    ("modules = {name: importlib.import_module(name) for name in manifest['modules']}", '''# Preload the versioned preparer under the frozen controller's bare import.
        name = 'prepare_registration'
        path = ROOT / manifest['modules'][name]['path']
        if name not in sys.modules:
            selected = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(selected)
            sys.modules[name] = module
            try:
                selected.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(name, None)
                raise
        modules = {name: importlib.import_module(name) for name in manifest['modules']}'''),
])
copy(pkg+'native_supervisor_authority.py', pkg+'native_supervisor_authority_v2.py', [
    ('native_attribution_controller as composition', 'native_attribution_controller_v2 as composition'),
    ('native_attribution_registration as draft', 'native_attribution_registration_v2 as draft'),
    ('notes/claudecode_direct/prepare_direct.py', 'notes/claudecode_direct/prepare_direct_v2.py'),
    ('d30e55e007a0ca178667516c089ad38055f339b3f9fa8e60cc43f23767b1e9c8', 'V2_DIRECT_DIGEST_PENDING'),
    ("return {'source_commit': head(),", "return {'authority_version': 2, 'controller_sources_sha256': composition.SOURCES_SHA256,\n            'source_commit': head(),"),
    ("extra = {name: importlib.import_module(name) for name in ADDITIONAL}", '''name = 'prepare_direct'
        if name not in sys.modules:
            selected = importlib.util.spec_from_file_location(name, ROOT / ADDITIONAL[name]['path'])
            module = importlib.util.module_from_spec(selected)
            sys.modules[name] = module
            selected.loader.exec_module(module)
        extra = {name: importlib.import_module(name) for name in ADDITIONAL}'''),
])
# External cases are explicit caller evidence, never an implicit study roster.
path = ROOT/base/'prepare_registration_v2.py'
text = path.read_text()
text = text.replace('parser.add_argument("--projects", required=True,', 'parser.add_argument("--external-canary", type=Path, help="JSON external case metadata, with project, source_manifest, chunks and profile")\n    parser.add_argument("--external-sources", type=Path, help="Optional external capture directory to pin")\n    parser.add_argument("--projects", required=True,')
start = text.index('    external = HERE / "external_clinical"')
end = text.index('    available = ', start)
text = text[:start] + '''    external = args.external_sources
    external_metadata = None
    external_status = "awaiting_source_registration"
    if args.external_canary:
        external_metadata = json.loads(args.external_canary.read_bytes())
        external_registry = load_registry(Path(external_metadata["source_manifest"]))
        project = external_metadata["project"]
        if not external_registry.declares(project) or project in projects:
            parser.error("external project must be declared and distinct from the primary roster")
        cases.append({"project": project, "manifest": str(external_registry.path),
                      "bundle": str(external_registry.bundle(project)),
                      "chunks": external_metadata.pop("chunks"), "profile": external_metadata["profile"],
                      "replicates": 1, "purpose": "external_general_user_canary"})
        external_status = "registered"
''' + text[end:]
start = text.index('    for path in sorted(external.iterdir()):')
end = text.index('    jobs = []', start)
text = text[:start] + '''    if args.external_canary:
        pins[str(args.external_canary.resolve())] = sha(args.external_canary)
    if external:
        for path in sorted(external.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                pins[str(path)] = sha(path)
''' + text[end:]
start = text.index('"external_canary": {')
end = text.index('                       "synthetic_fixture":', start)
text = text[:start] + '"external_canary": external_metadata,\n' + text[end:]
# Render-only cannot require a native executable, even for its version string.
text = text.replace('"claude_version": subprocess.check_output(["/Users/marcin/.local/bin/claude", "--version"], text=True).strip(),', '"claude_version": None if args.render_only else subprocess.check_output(["/Users/marcin/.local/bin/claude", "--version"], text=True).strip(),')
path.write_text(text)
path = ROOT/'notes/claudecode_direct/prepare_direct_v2.py'
text = path.read_text().replace('import prepare_registration as generation', 'import prepare_registration_v2 as generation')
path.write_text(text)
