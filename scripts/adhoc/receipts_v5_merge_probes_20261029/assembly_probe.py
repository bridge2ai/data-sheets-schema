# Purpose: repeat claude's assembly identity probe for N1/N3/N4, 2026-10-29.
# Inputs: selected tree via Python imports; output: JSON assembly/descriptor digests.
# Copied from /private/tmp/claude-501/receipts-v5-IDc5/scripts/assembly_probe.py.
import json, sys
from data_sheets_schema import api_runner as api, shared_generation as sg
out = {}
out["v10_sg1_r25"] = api.assembly_digest(25, api_playbook_version=2, receipt_completion_version=2, shared_generation_version=1)["sha256"]
try:
    out["routing_sg2_r27"] = api.assembly_digest(27, api_playbook_version=3, receipt_completion_version=3, shared_generation_version=2)["sha256"]
except Exception as e:
    out["routing_sg2_r27"] = f"error {type(e).__name__}: {e}"
out["r24_rc1"] = api.assembly_digest(24)["sha256"]
out["r8_rc1"] = api.assembly_digest(8, receipt_completion_version=1)["sha256"]
d1 = sg.descriptor()
out["descriptor_v1"] = json.dumps(d1, sort_keys=True)[:0] or __import__("hashlib").sha256(json.dumps(d1, sort_keys=True).encode()).hexdigest()
try:
    from data_sheets_schema.source_heading_runtime import MODES
    d2 = {m: sg.descriptor(version=2, condition=m) for m in MODES.values()}
    out["descriptor_v2_routing_code"] = {m: {k: v[:12] for k, v in d["routing_code"].items() if k.endswith(("receipts.py", "report_claims.py", "derive_core.py", "receipt_origin.py", "canary.py"))} for m, d in d2.items()}
except Exception as e:
    out["descriptor_v2_routing_code"] = f"error {type(e).__name__}: {e}"
print(json.dumps(out, indent=1, sort_keys=True))
