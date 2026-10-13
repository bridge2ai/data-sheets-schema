# Retained one-call schema profiler

Purpose: reproduce the first #5015 schema admission microprofile. Date: 2026-10-12. Related issue: bridge2ai/data-sheets-schema#5015; no PR yet.

Original source: `/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-admission-profile01/profile_schema_once.py`. The migrated script adds only a documentation header; its executable AST is unchanged. Its adjacent `input-pins.json` and historical README are byte-exact copies. Original and migrated SHA-256 values are recorded in the companion migration manifest.

No path logic changed: the script finds input-pins.json beside itself, then checks the declared owned checkout/source/schema. Those historical source pins intentionally fail after withdrawing the catalog candidate. A separately retained successor configuration is required for a new measurement; never overwrite this historical configuration. Existing external result locations remain evidence, and new runs require a fresh external output directory. Root owns all project runtime.
