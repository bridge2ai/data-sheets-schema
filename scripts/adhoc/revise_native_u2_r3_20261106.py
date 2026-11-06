# Purpose: apply U2 review corrections (#5508), 2026-11-06.
# Inputs: round-2 v2 sources. Outputs: revised v2 sources only.
from pathlib import Path
R = Path(__file__).resolve().parents[2]
p = R/'notes/matched_cborg_2026-09-13/prepare_registration_v2.py'
s = p.read_text().replace('SERIES = "generalized_v10_2026-09-13"\n', '')
s = s.replace('profile_basis="stated by the registered caller"', 'profile_basis="declared by source manifest"').replace('job.get("run_date", "2026-09-14")', 'job["run_date"]')
for arg in ('cohort', 'label-date', 'run-date'):
    import re
    s = re.sub(r'parser.add_argument\("--'+arg+r'", default="[^"]+"\)', 'parser.add_argument("--'+arg+'", required=True)', s)
s = s.replace('    parser.add_argument("--render-only",', '    parser.add_argument("--series", required=True)\n    parser.add_argument("--authorization", required=True)\n    parser.add_argument("--additional-usd", type=float, required=True)\n    parser.add_argument("--per-attempt-usd", type=float, required=True)\n    parser.add_argument("--claude-executable", required=True)\n    parser.add_argument("--render-only",')
s = s.replace('"--external-sources", type=Path,', '"--external-sources", type=Path, action="append", default=[],')
s = s.replace('"profile": "bridge2ai"', '"profile": profiles.declared_profile(registry.path) or "neutral"')
s = s.replace('    external = args.external_sources\n', '')
s = s.replace('        cases.append({"project": project', '        declared = profiles.declared_profile(external_registry.path) or "neutral"\n        if external_metadata.get("profile", declared) != declared:\n            parser.error("external profile differs from source manifest")\n        cases.append({"project": project')
s = s.replace('external_metadata["profile"]', 'declared')
s = s.replace('    if external:\n        for path in sorted(external.rglob("*")):', '    for external in args.external_sources:\n        for path in sorted(external.resolve().rglob("*")):')
s = s.replace('    jobs = []', '    if external_metadata:\n        for key in ("source_manifest", "applicability_context"):\n            if external_metadata.get(key):\n                path = Path(external_metadata[key]).resolve()\n                pins[str(path)] = sha(path)\n    jobs = []')
s = s.replace('for profile_name in ("neutral", "bridge2ai"):', 'for profile_name in sorted({"neutral", *(case["profile"] for case in cases)}):')
s = s.replace('"schema_version": 1, "series": f"{args.cohort}_{args.label_date}"', '"schema_version": 2, "series": args.series')
s = s.replace('"awaiting_preflight_review" if external_status == "registered" else "draft_external_sources_pending"', '"awaiting_preflight_review"')
s = s.replace('["/Users/marcin/.local/bin/claude", "--version"]', '[args.claude_executable, "--version"]')
s = s.replace('"additional_usd": 200, "per_attempt_usd": 5, "authorization": "user: +$200, 2026-09-13"', '"additional_usd": args.additional_usd, "per_attempt_usd": args.per_attempt_usd, "authorization": args.authorization')
s = s.replace('"agentic_cli_budget_flag_default_usd": 5', '"agentic_cli_budget_flag_default_usd": args.per_attempt_usd')
s = s.replace('save(output / "registration.json", manifest)', 'save(output / "registration.json", envelope(manifest))')
s = s.replace('"additional_budget_usd": 200', '"additional_budget_usd": args.additional_usd')
s = s.replace('\ndef main():', '''
def envelope(registration):
    """V2 wire shape: frozen v1 consumers cannot read required top-level fields."""
    from data_sheets_schema.native_attribution_controller_v2 import SOURCES_SHA256
    return {"authority_version": 2, "controller_sources_sha256": SOURCES_SHA256,
            "registration": registration}


def require_envelope(value):
    """Admission interface for U3; this does not grant permission to launch."""
    from data_sheets_schema.native_attribution_controller_v2 import SOURCES_SHA256
    if (set(value) != {"authority_version", "controller_sources_sha256", "registration"}
            or type(value["authority_version"]) is not int or value["authority_version"] != 2
            or value["controller_sources_sha256"] != SOURCES_SHA256
            or not isinstance(value["registration"], dict)
            or value["registration"].get("schema_version") != 2):
        raise ValueError("v2 launch requires an exact v2 authority envelope")
    return value["registration"]


def main():''')
s = s.replace('    canary_order =', '    import math\n    if any(not math.isfinite(v) or v <= 0 for v in (args.additional_usd, args.per_attempt_usd)) or not args.authorization.strip():\n        parser.error("positive finite budgets and explicit authorization are required")\n    canary_order =',1)
p.write_text(s)
p = R/'notes/claudecode_direct/prepare_direct_v2.py'; s = p.read_text()
s = s.replace('DEFAULT_COHORT = "generalized_direct_v1"\n','')
s = s.replace('    bundle = registry.bundle(project)', '    if not registry.declares(project):\n        raise DirectStop("project must be declared by the source registry")\n    bundle = registry.bundle(project)')
s = s.replace('"profile": "bridge2ai"', '"profile": generation.profiles.declared_profile(registry.path) or "neutral"').replace('profile_basis="stated by the registered caller"', 'profile_basis="declared by source manifest"')
s = s.replace('"kind": "d4d_direct_arm_registration", "schema_version": 1', '"kind": "d4d_direct_arm_registration_v2", "schema_version": 2')
s = s.replace('save(path, registration)', 'save(path, generation.envelope(registration))')
for arg in ('claude-executable','cohort','label-date','run-date','runaway-guard-usd'):
    s = re.sub(r'    parser.add_argument\("--'+arg+r'", default=.*\)\n', '    parser.add_argument("--'+arg+'", required=True)\n', s)
p.write_text(s)
p=R/'src/data_sheets_schema/native_attribution_controller_v2.py'; s=p.read_text().replace("        modules = {name:", "        sys.modules['prepare_registration_v2'] = sys.modules['prepare_registration']\n        modules = {name:"); p.write_text(s)
