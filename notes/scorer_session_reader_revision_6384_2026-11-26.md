# Scorer session-reader revision for issue 6384

This acceptance-code revision starts from `047137b9ea30603abbe3ede25a15c4a753f71978`. The measured runner remains preserved there and in the earlier scoring checkouts. New plans and publications identify this revision through `scorer_instrument.runner_sha256`, alongside the existing instrument id and prompt hash.

| Reader | Runner SHA256 |
| --- | --- |
| Measured reader | `b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9` |
| Revised reader | `45324f05ef4360f95620c5e9a37d7896661321177242f700f25bd22fe72cf51b` |

The semantic instrument labels remain stable. The complete recorded instrument identity changes because the runner hash changes. Comparing or pooling measurements must include that hash. Prompt bytes, composed definitions, schemas, evidence authority and selected record/scope inputs retain their measured identities. `verify_session_reader_plan_revision_6384_20261126.py` builds thirty plans and compares each entire plan to its measured counterpart through the existing explicit path-relocation function, allowing only the changed runner hash afterward.

## Ownership rule

The reader loads the session metadata and verifies its ancestry graph before processing root and child histories in parent-first order. A child's spawn mode comes from exactly one correlated spawn call and output in its retained parent's already qualified owned history. An omitted mode retains the documented default of `all`; only explicit `none` establishes a fresh child. Missing optional child metadata alone never establishes freshness.

A fresh child owns its task/context pairs from the start of its log. Its settings marker may follow its first context, as in both retained false-refusal shapes. The fresh shape requires absent or null fork-origin and copied-history-ordinal metadata. Contradictory values refuse. A forked child retains the strict settings-marker boundary and checks its optional fork origin and ordinal against that boundary and parent.

Every inherited model-bearing context must equal a retained ancestor-owned context payload and a context retained in its direct parent's log. Equality uses canonical JSON serialization so differing JSON types cannot compare equal accidentally. Root/child model, effort, working directory, task/context pairing, root-turn agreement, invocation window, ancestry, owned call/output correlation, inherited call/output correlation and complete child-log coverage remain checked.

## Offline replay boundary

`replay_scorer_session_identity_6384_20261126.py` reads explicit original run roots and saved metadata, stdout and session logs. Its reader sees only an allowlisted snapshot of those identity inputs. The helper checks the input inventory and hashes afterward and writes its separate structural report outside the run roots. It suppresses dynamic error values and exports no message bodies, response content or scores. All supplied run roots and explicit run directories remain protected from report writes even when their runs are excluded from the selected census (review issue 6397).

Identity replay does not validate an evaluation, create a candidate, publish an output or change an original refusal receipt. In particular, a validation-refused run may pass identity replay while retaining its original validation refusal. The owner has not authorized recovery or revalidation of any refused output under this revision.

The reduced tests preserve the observed fresh one-turn and two-turn layouts and the forked prefix layout. Controls require refusal for parent-turn spoofing, missing task evidence, wrong model/effort/cwd, missing logs, contradictory metadata, altered inherited payloads, ancestry/correlation failures and invocation-window violations.
