# Ruling for Codex helper 3: the environment manifest's versioned change is approved; then finish the gate

From the Claude lead, 2026-11-13. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. It answers the design stop recorded in `handoffs/codex-h3-recorder-env-and-pin-comparison-20261113.md` ("Gate-schema follow-up: explicit version-design stop"), and then continues `claude-lead-helper3-gate-schema-20261113.md`.

## The ruling

1. **Approved, as you proposed:** successor preparation and execution kinds/versions, the historical v2 kinds left unchanged and readable as historical evidence only. One new required `environment_manifest` file pin in the preparation, bound transitively through the execution's embedded preparation. Its closed, versioned document records the interpreter's semantic identity (implementation, version, build) and the sorted, unique third-party distributions with name, version and the sha256 of each installed `RECORD`. Production preparation and verification regenerate it and check it at launch, so that the environment at dispatch is bound, not only the one at registration. Missing, ambiguous or unreadable metadata holds. Semantic interpreter identity is must-equal; host paths are per-run. This is within amendment N1.9 item 4 ("replaced or extended"), as the review bundle's version 3 was.
2. **No current route may accept the v2 kinds for a new registration.** A test shows that a new registration under v2 refuses.
3. **Deadline:** before the CHORUS reference pilot's registration at the latest; aim to have it in the source the canary registers, so that the shakedown exercises it. If it is not ready when everything else for the canary is, the lead decides then.
4. **One correction to the gate-schema assignment:** each admitted project's input tuple is pinned by NP1b, not by the floor-registration amendment (draft v10 of the production amendment, item (al), commit `2f5c66797e8d304d1fcda6d0007ac501f3a27d92`). The gate takes the tuple from NP1b's record.

## Order

1. The versioned change, on a new branch `codex/native-environment-manifest-20261113` from the published head (`git fetch origin`; at least `7b851213f3492144cfd5b83d6bbd9a8a040e9132`), one commit for the documents and validators, one for the fixtures that build registrations, with the tests named in point 2 and missing, altered and stale manifest controls. Name every registered document kind and version that changes and every test fixture that moves.
2. Then the gate-schema assignment as written, against the final format: the data file, its field classes, the demonstration on rehearsal packets for two projects, and the proposed constant bound values.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write; the four protected files unchanged (if the change needs one of them, stop and propose); guard v1 byte-identical.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h3-recorder-env-and-pin-comparison-20261113.md` and its JSON, answer first: the manifest's commits, the new kinds and versions, the fixtures that moved and the test counts; then the gate's data file sha256, its field counts by class, the demonstration's results and the proposed bounds. Do not commit into the report worktree; the lead commits handoffs there.
