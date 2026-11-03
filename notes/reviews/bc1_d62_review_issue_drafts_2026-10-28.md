# Offline review issue drafts — 2026-10-28

These record the findings from the separate read-only diff review. GitHub
publication is deferred because this task explicitly prohibits network/gh.
R1–R3 belong in this change and are addressed with negative tests. R4 remains
recorded for separate triage.

## R1 — constrain BC1 selector getters to the scalar fields actually read

The first selector proof permitted any literal `getattr(spec, name)`. A future
getter for `__dict__` could expose mutable state even while every direct use of
the name `spec` looked read-only. Require the finite scalar field set used by
the current validator, and reject a seeded `__dict__` getter.

Disposition: fixed in the scanner; no production selector or wire change.

## R2 — require effective backend entry definitions

The first backend proof checked the dispatcher body but did not reject a
decorated, duplicated or rebound `run` entry. Require one undecorated effective
definition on both sides of the dispatch, in addition to the exact selector
and forwarded argument checks.

Disposition: fixed in the scanner; negative mutation tests cover the entry
identity. No A14 change or protected-file edit is involved.

## R3 — retain schema additions through D59's local assignment

The full regression run exposed one remaining F4 failure: the schema-form
description named only `generation_context`, because the old addition scanner
looked only for calls directly inside a text block. D59 assigns `schema_text`
in the BC1 and legacy branches first. Derive both builders from that exact
branch shape, prove the only two assignments and their ordering, authenticate
the imports, and retain each branch guard in the report.

Disposition: fixed in the scanner, preserving the existing failing assertion;
negative tests cover changed inputs, imports, builders and extra assignments.

## R4 — existing BC1 project allowlist remains a specificity finding

The completed scan reports 101 findings overall, including five matches on
the existing six-project `PROJECTS` tuple in `bc1_registration.py`. All five
are classified `run_shaping`, `model_facing: false`; there are no BC1
model-facing violations in the saved diagnostic. The tuple and its project
admission use predate D62 and are visible at `8f83d6cb3`.

Disposition: leave reported. Expanding project admission or granting a scanner
exception is separate from repairing F4's failed derivation/tests. Do not
describe this completed scan as a clean neutrality verdict. No exemption added.
