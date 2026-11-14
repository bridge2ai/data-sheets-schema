# Native loader lifetime probe: issue #5834

On 2026-11-11, one import-only probe reproduced the WP3 snapshot-binding refusal in **4.280125 seconds** (4.280 seconds rounded), with exit code 1 and no timeout. This was the expected diagnostic refusal, not a successful generation. No fixture construction, model calls, or native executable launches occurred. The helper did not manually mutate registries or guards; it exercised the genuine loader context managers.

The working directory was:

`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-expired-capture-order-20261111`

The exact invocation was:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-89c28cb97dea-cpu-monitoring-post-wp3-20261111/venv/bin/python scripts/adhoc/lead_probe_loader_lifetime_5834_20261111.py
```

The helper supervised one child using that existing interpreter, with a 26-second timeout, disabled bytecode writes, and this checkout's `src` directory first on the child's import path. It obtained genuine `dependency_identity()`, entered `launch_derivations()` and actual `loaded_controls()`, entered **two stacked `loaded_dependencies()` scopes inside controls**, exited both, and then imported `api_runner` and `native_shared_render`.

Before and after the run, HEAD was `e282f05960a2b397844acb3ac5f140b1fe192cd8`; Git status for `src` and `tests` was empty. The helper's fingerprint of tracked package/test Python paths and file hashes was unchanged:

`41a422733097cf42ccdb4e0b81253115201f67e3236bb54f858f0ebe4fa07d4f`

This fingerprint covers the helper's `git ls-files -z 'src/data_sheets_schema/*.py' 'tests/*.py'` selection; it is not a hash of every repository file.

The first nested dependency scope loaded `schema_snapshot` through this authority's `_VerifiedBytesLoader`. The same object remained the canonical `sys.modules` snapshot through both scope exits, and its `module_source_identity()` attestation succeeded. At the late render import's refusal, `guard.snapshots` was exactly that canonical object and the selection's `_capture_native_schema` was exactly its producer. The consumer registry had **no snapshot entry**. There was no different registry snapshot, ordinary-import snapshot, or cross-authority object in this witness. No donor had yet been assigned: the first selection binding failed before that assignment.

The error was:

```text
ValueError: verified schema snapshot binding differs from catalog guard
```

The stacked probe is not the exact dependency-scope ordering of the failing integration. AGY2's separate pytest regression uses **two sequential dependency scopes inside controls**, matching the actual ordering, and independently reproduced the same error in **5.26 seconds**, as reported by the lead. That result is separate from this probe and is not included in its artifact hashes.

## Preserved artifacts

Paths below are relative to the working directory above. The executed helper and raw results were preserved without rerunning or rewriting them.

| Artifact | SHA256 |
|---|---|
| `scripts/adhoc/lead_probe_loader_lifetime_5834_20261111.py` | `7b4dda1015ac9f811e21992e32f9689218f885d0a594496c41601c9059f79a10` |
| `tmp/lead-loader-5834/probe.json` | `f402b8fcce27656742faa03e656b9314502cddc58108a6b9fff5cbb31eec5e60` |
| `tmp/lead-loader-5834/supervisor.json` | `f6cfd09c9ddbdb55e81780605f2c3c573c4cf1fe4c5f169955a23210db87725e` |

The evidence isolates an import/registry lifetime mismatch. It does not establish that a corrected binding reaches reservation, passes freshness, or completes D4D generation.
