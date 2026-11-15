#!/usr/bin/env python3
"""Rotate the controller and scanner pin chain after merging #6259 and the v3 fixes.

Purpose: run_native_canary.py (999146aa6, #6259), audit_controls/native.py
(#6259) and native_environment_manifest.py (codex/v3-merge-fix) moved. This
script recomputes every dependent pin from the working bytes, in dependency
order, and asserts each result equals the helpers' proposals before writing.
Proposals: handoffs/codex-controller-6259-6258-20261115.md and
codex196-v3-merge-fix-20261115.md. Input: checkout root (cwd). Output:
edited files; prints each rotation. Draft PR 5968. Claude lead, 2026-11-15.
"""
import ast, hashlib, re
from pathlib import Path
R = Path('.')
def sha(p): return hashlib.sha256((R / p).read_bytes()).hexdigest()
def sub(p, old, new, count=1):
    t = (R / p).read_text()
    assert t.count(old) == count, (p, old[:12], t.count(old))
    (R / p).write_text(t.replace(old, new)); print(f'{p}: {old[:12]} -> {new[:12]} x{count}')
SC = '.claude/skills/d4d-generation-specificity-audit/scan.py'
NC = 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
AN = 'notes/matched_cborg_2026-09-13/audit_controls/native.py'
CE = 'notes/matched_cborg_2026-09-13/audit_controls/checkpoint_eligibility.py'
assert sha(NC) == 'bfa1da119bbb0778b7e1f10d2c55306a2e191fef9133da40de403f33c1a58b1c'
for v in ('v1', 'v2'):
    m = f'src/data_sheets_schema/native_controller_sources_{v}.json'
    sub(m, 'da00584aa4e3129e6d1ed12638f5149b716e4fb9', '999146aa625512cf5f27f7cf7b3667c3ce0bc882')
    sub(m, '5464a25b7fa6153fb4aa1b5c49435cc23a9fd34fa2cb395acc657f26c3b38fcb', sha(NC))
v1, v2 = sha('src/data_sheets_schema/native_controller_sources_v1.json'), sha('src/data_sheets_schema/native_controller_sources_v2.json')
assert v1 == '43bcecfbac8eb8487f5e4feb474c34f0ba7c6af9bcf7b111bde2710196a5a6c3', v1
assert v2 == '99f189f810c83fd78629dd60667fa9016131847389c44fd401f3be86c2d0e60b', v2
sub('src/data_sheets_schema/native_attribution_controller.py', 'ece499cb7e82b19a950c70ca6a50079091ffe7f3c362df48b2e183dfa06695f7', v1)
sub('src/data_sheets_schema/native_attribution_controller_v2.py', 'e500cb15c54d2db9a05a20b2259b67943b8f346f2221250cfd6f472ca6412e0c', v2)
sub('src/data_sheets_schema/native_shared_authority_wire.py', 'e500cb15c54d2db9a05a20b2259b67943b8f346f2221250cfd6f472ca6412e0c', v2)
c2 = sha('src/data_sheets_schema/native_attribution_controller_v2.py')
assert c2 == '01e290301af5322b7967f8abb8a8242e9adad54b15fcd9d2322ec1f6d458b956', c2
wire = sha('src/data_sheets_schema/native_shared_authority_wire.py')
assert wire == 'ef5bd0e1fb248597a53c0ba2973b94708a817abf04c1e13bea30811222797d99', wire
env = sha('src/data_sheets_schema/native_environment_manifest.py')
assert env == '790040b275d4d67aed40a6805835bb688030ec0ef3e7e004984aadcf4a2c10b7', env
sub(SC, "'src/data_sheets_schema/native_controller_sources_v2.json': 'e500cb15c54d2db9a05a20b2259b67943b8f346f2221250cfd6f472ca6412e0c'",
    f"'src/data_sheets_schema/native_controller_sources_v2.json': '{v2}'")
sub(SC, "'src/data_sheets_schema/native_attribution_controller_v2.py': '75c748000983aa82e8e07bbc24fa888cf3b995685e4e8726e1e6dcf10af9004f'",
    f"'src/data_sheets_schema/native_attribution_controller_v2.py': '{c2}'")
sub(SC, '270672bbd40559552ba308d1536f859108774e5719807db5309142e013590ed4', wire)
sub(SC, '72003fcee74562ce8f4a17eda49218830d44a74aebbee3c27b0b33fe987655e6', env)
an = sha(AN); assert an == '004c10ca5d3c6c5b636d9f86cad6d1a8a327945738f0e13e7c14c69cb33a6818', an
sub(CE, "        'e7279038e22984e0cb652c6cf2ef7576dc10c430224766cf1f18cbccf7a73ea5'}),",
    "        'e7279038e22984e0cb652c6cf2ef7576dc10c430224766cf1f18cbccf7a73ea5',\n"
    "        # #6259 carries structured cleanup errors onto native_stop;\n"
    "        # `classify_command` is byte-identical.\n"
    f"        '{an}'}}),")
print('scan.py', sha(SC))
