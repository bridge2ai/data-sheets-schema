# Handoff: `G3` (`agy3`) — Final Generation Acceptance Guide

## Summary

- **Owner:** `G3` (`agy3`)
- **Worktree:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-final-generation-acceptance-guide-20261110` (sparse-checkout cone: `docs`)
- **Branch:** `agy/final-generation-acceptance-guide-20261110`
- **Base Commit (`origin/main`):** `7233f193ad102a8488b31ec7333662c8fefaa996`
- **Commit History:**
  - `36d9bb25be456b547ccf40677b0beae1751512d9` (initial guide)
  - `36526c0379a77a5d2a97c7e4db48d005e6b55337` (resolved `#5795`, `#5797`, and main `#5796` items)
  - **Current `HEAD` SHA:** `c0d667fbc721f7c6984e2092395c33e37324ea1c` (resolved `#5796` residuals)
- **Owned File:** `docs/final-generation-acceptance.md` (`96` lines, `8,575` bytes, SHA-256 `b892f38bc57d615387523f871e85b0fcbd5e3ad804c4dfcfda870dd17060a761`, `0` at-sign characters)
- **Runtime / Test Budget Used:** `0` tests/builds executed; `0` subprocess runtime budget consumed.
- **Primary Checkout / Native Worktree State:** Untouched.

---

## Review Findings Addressed Through `c0d667fbc721f7c6984e2092395c33e37324ea1c`

1. **`#5795` (Resolved in `36526c037`):**
   - Removed unsupported `typed_audit` flags and linked directly to [typed-audit-offline.md](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/docs/typed-audit-offline.md).
   - Corrected `poetry run d4d api status` to take no `--project` or `--label` options.
   - Stated that `poetry run d4d review pack` creates the bundle only and an independent reviewer must populate `<PROJECT>_review.yaml` before `poetry run d4d review check --strict`.
2. **`#5796` (Resolved in `36526c037` + `c0d667fbc`):**
   - Referred to the **pinned integrated schema** in the introduction and Section 3.2 rather than hardcoding `3.2.0` (`G2` advances to `3.2.1`).
   - Stated the exact container and `Person` paths: `creators` is a list of `Creator` containers (`Creator.principal_investigator` takes a nested `Person` object) and `maintainers` is a list of `Maintainer` containers (`role` plus scalar string `maintainer_details`, with no nested `Person`). Explicit `Person` object paths (`Creator.principal_investigator`, `LicenseAndUseTerms.contact_person`, and `DataGovernance.committee_contact`) must be inline `Person` mappings, never bare name strings.
   - Stated that scalar narrative slots (for example `Purpose.response`) and `FileCollection.collection_type` (`#2975`) must be scalar strings, while `LicenseAndUseTerms.data_use_permission` is a list.
   - Described observable `d4d derive core` and `make validate-d4d-pair` behavior while keeping separate full/Core `d4d validate` checks mandatory, and documented the API record guard (`id` required, unknown top-level keys rejected, `>= 5` top-level keys).
3. **`#5797` (Resolved in `36526c037`):**
   - Stated unconditionally that `N1` exercises isolated receipt, schema/pair, and source-review components without composing the full native admission, process-lifecycle, typed-assembly, and fifteen-gate completion path, so completing `N1` is **always component-only evidence** and does not establish whole-native stub refusal or whole-native acceptance.

---

## STATUS (`agy3` / Owner `G3`)

- **2026-11-10 (`G3` / `agy3` — Final Generation Acceptance Guide `#5796` residuals resolved at `c0d667fbc`):** Updated `docs/final-generation-acceptance.md` in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-final-generation-acceptance-guide-20261110` on branch `agy/final-generation-acceptance-guide-20261110` and committed `c0d667fbc721f7c6984e2092395c33e37324ea1c` (`96` lines, `8,575` bytes, SHA-256 `b892f38bc57d615387523f871e85b0fcbd5e3ad804c4dfcfda870dd17060a761`, `0` at-sign characters, clean `git diff --check`). The commit resolves all remaining `#5796` items: refers to the pinned integrated schema instead of hardcoding `3.2.0`, clarifies `Maintainer` (`role` plus scalar `maintainer_details`, no nested `Person`), names the explicit `Person` paths (`Creator.principal_investigator`, `LicenseAndUseTerms.contact_person`, `DataGovernance.committee_contact`), replaces `DataUsePermission.data_use_permission` with `LicenseAndUseTerms.data_use_permission`, and specifies scalar narrative slots (for example `Purpose.response`). Zero tests or builds executed (`0` runtime budget used); primary checkout and native worktree untouched.

---

## Follow-On Helper: `scripts/adhoc/check_final_generation_products_20261110.py` (Frozen for Lead Run)

- **Reserved File:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110/scripts/adhoc/check_final_generation_products_20261110.py` (`723` lines, `0` at-sign characters; frozen).
- **Interrupted Attempt (`task-2382`, `PID 10706`):**
  - **Command:**
    ```bash
    /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110/scripts/adhoc/check_final_generation_products_20261110.py --git-repo /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110 --g2-root /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110 --base-rev 7233f193ad102a8488b31ec7333662c8fefaa996 --output /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110/scratch-final-readiness-lead-20261110/products-1.json
    ```
  - **Outcome:** Tool backgrounded at `10s`; lead observed `PID 10706` still running at `48s` and sent `SIGINT` at `76s` (#5806/#5807). No output file was written. The `--output` argument on that attempt was also wrongly nested inside the lead worktree instead of the sibling directory `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-final-readiness-lead-20261110/products-1.json`.
  - **Exact Traceback Location (`task-2382.log`):**
    - `check_final_generation_products_20261110.py` line `686` (`main()`) $\to$ line `584` (`check_owl_isomorphism(...)`) $\to$ line `188` (`graph_diff(to_isomorphic(substituted_base), to_isomorphic(g2_graph))`), after `isomorphic(substituted_base, g2_graph)` at line `187` had already returned
    - `rdflib/compare.py` line `597` (`graph_diff`: `cg1 = to_canonical_graph(g1)`) $\to$ line `590` (`to_canonical_graph`: `graph += _TripleCanonicalizer(g1).canonical_triples(stats=stats)`) $\to$ line `494` (`canonical_triples`: `coloring = self._refine(coloring, coloring[:])`) $\to$ line `363` (`_refine`: `coloring.remove(c)`) $\to$ `KeyboardInterrupt`.
- **Frozen Source Fixes Applied (`#5804`, `#5805`, `#5807`):**
  - **`#5804`:** Expects `d4d_description` as `desc[:100] + "..."` and base `comment` `"Free text/narrative field - no URI needed; TTL names only D4D terms, which are not alignments"` in `d4d_rocrate_sssom_comprehensive.tsv`.
  - **`#5805`:** Preserves and compares all `#` comment header lines in both comprehensive SSSOM TSVs (`compare_comment_headers`), permitting only `# Date: ...` and the exact `#   free_text: 13` $\to$ `#   free_text: 12` and `#   unmapped: 84` $\to$ `#   unmapped: 85` transitions.
  - **`#5807`:** Removed redundant `graph_diff` / `to_isomorphic` calls and diff-count assertions; retains `rdflib.compare.isomorphic(substituted_base, g2_graph)` called once alongside the exact ground-triple prechecks; sets `rdflib.NORMALIZE_LITERALS = False` across both Turtle parses and expected literal construction (restored in `finally:`); arms an in-process POSIX `120`-second `SIGALRM` / `ITIMER_REAL` deadline raising `TimeoutError`; defaults `--output` to `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-final-readiness-lead-20261110/products-1.json` and rejects any output path inside `git_repo` or `g2_root`.
- **Runtime Status:** `RELEASE BUDGET` — source frozen; lead owns the single `120`-second run.
