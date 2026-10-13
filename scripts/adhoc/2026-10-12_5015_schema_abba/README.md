# Four-call schema admission comparison

Purpose: evaluate the bounded per-admission event replay for #5015. Date: 2026-10-12; no PR yet. Root alone executes this driver.

The current parser is compared with the literal old depth-check plus UniqueLoader operation by changing only `audit_omissions._schema_yaml`, restored in `finally`. Four real `_schema` calls use the same genuine captured merged schema in old/new/new/old order. Capture, imports, hash checks and result serialization are outside timing; fresh byte/depth/root/closure checks and actual catalog construction remain inside every call. The catalog is compared byte-for-byte after deterministic JSON encoding. No cache or parser stubs are added.

The input manifest binds eight exact checkout files. This directory must be mirrored byte-for-byte to the owned task branch before use. A new source revision requires a new, separately saved input manifest; do not overwrite retained measurement inputs.

Root-only command, after focused tests and static review:

```sh
/private/tmp/d4d-performance-implementation-20261012/.venv/bin/python /private/tmp/d4d-performance-implementation-20261012/scripts/adhoc/2026-10-12_5015_schema_abba/benchmark_schema.py --root /private/tmp/d4d-performance-implementation-20261012 --output /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-admission-abba01-results
```

The output directory must be new and external. Results include raw wall/thread CPU times, catalog sizes/hashes/equality, source preservation, restored-binding state, versions/load and process high-water RSS. No hooks count parser branches, so fallback frequency is intentionally unmeasured. RSS is not an isolated per-call allocation measurement. This small sequence establishes no statistical significance or whole-pipeline speedup.
