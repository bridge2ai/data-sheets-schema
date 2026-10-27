# Completed BC1 validation evidence — 2026-10-27

These archives preserve three completed offline batches. They do not establish
a combined green suite, installed protected-hook acceptance, scientific
acceptance or permission to launch. The longer public-pipeline batch on the
original `17ca65b0a` checkout is still pending and is deliberately absent here;
its completed evidence, including its known streaming-fixture failures, must be
retained separately when it finishes. The main implementation report remains
pending that result.

| Archive | Frozen source | Reported pytest outcome | Driver |
| --- | --- | --- | --- |
| `run-01.tar.gz` | `b2525adb92159776d3fbeb22ecf41f564143462a` | 100 passed, 18 setup errors; 34.74 s | Exit 1; source unchanged; 38.2412 s |
| `run-02.tar.gz` | `17ca65b0a00f8f3c665e1f7d343b93b121176320` | 317 passed, 1 skipped, 12 warnings; 1490.60 s | Exit 0; source unchanged; 1533.1525 s |
| `run-03.tar.gz` | `f811ac0840775984e54efa573e873224c7d1831e` | 18 runtime cases passed; 76.57 s | Exit 0; source unchanged; 79.3477 s |

The initial errors are preserved verbatim. The invented runtime fixture had
omitted required input-identity fields; the existing snapshot guard correctly
refused it. The later fixture supplies captured bundle/chunk/source-manifest
identity and an explicit instruction hash before creating its ledger. The final
runtime mirror adds the existing `FakeMessages.stream` interface to its fake
client, preserving the real streamed call path and all assertions. That mirror's
production `src/` bytes are identical to `17ca65b0a`; its only pre-archive change
is the two-line test-client inheritance/import correction.

The legacy skip is
`test_registration_input_sizing::test_rendering_reproduces_the_chorus_v10_wire`:
it requires `D4D_CHORUS_V10_TYPED_RUN` to name the historical 2026-10-22a
intermediate directory. It is not counted as a pass. Timings are ordinary
functional-test evidence, with overlapping authorized work; they are not idle
host measurements.

[manifest.json](manifest.json) records exact input paths, every selected file's
SHA-256/size/mode, archive hashes, original outcome classification, excluded
directories and helper provenance. The existing repository helper
`scripts/adhoc/archive_n2_restack_validation_20261027.py` was run with these three
`--evidence` arguments under `/private/tmp/d4d-bc1-validation-20261027/`, in order:
`b2525adb9-bc1`, `17ca65b0a-legacy`, `f811ac084-runtime`. Its fresh `--output` was
this directory. It verified every archive's byte/mode roundtrip and rechecked
the selected originals unchanged. It makes no aggregate pass claim.

Only selected top-level JSON/log/XML evidence is archived. Complete synthetic
case/cache directories remain in their original external locations and are not
attested by this archive. Source files, original evidence and the active public
pipeline checkout were not modified. Archive timestamps are normalized; file
bytes and modes are preserved.
