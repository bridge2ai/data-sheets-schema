# E3 — smallest safe native redundant-work fix, read-only preparation

Inspect existing native source at d4d-executions/codex-native-u1u3 (5f4a8e211) and the reviewed native latency plan v3. Do not edit that worktree, run imports/tests or modify any production source. Native Codex owns all source changes.

Find one concrete smallest intervention supported by source: repeated schema/metadata derivation in make_case or a repeated verification cascade before reservation. Identify exact functions/callers, what is already cached, the immutable inputs and invalidation boundary, required refusal-equivalence cases and any protected packet dependency. Prefer reuse of an existing safe derivation scope over inventing an authority cache. Preserve current-byte validation, freshness, one-use/order semantics; never propose treating a previous successful authorization as current merely for speed.

Write at most two pages in lead handoffs/agy2.md with the proposed small diff boundaries and test selectors. Existing retained profiling can support call-count claims; do not call them fresh timings. Lead/native will decide and implement immediately after the observer canary evidence. No broad redesign, comprehensive new plan, Github writes or nested worker fanout.
