# Assignment to Codex helper 3: repair the three launch-sequence findings of your own review

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your handoff is accepted (`handoffs/codex-h3-all-project-prefix-and-cross-review-20261112.md`; branch commit `2f69089842c116f6ec0a86ebfbba0884e1e3a2b4`).

- **Part A:** all five projects pass the real-input prefix; the bundles and chunk manifests are current; the builder's CHORUS-only gate (H3-A1) is fixed in `0cf319823`. The size table goes into the production amendment. Kids First has no manifest entry, bundle or sources: noted, nothing to do.
- **Part B:** the three findings are accepted as you graded them and are filed: **#5989** (H3-X1), **#5990** (H3-X2), **#5991** (H3-X3). Amendment N1, draft v12, line 353 confirms the rule behind H3-X1: "A re-capture under D115 is a new start of the whole sequence, made by the owner or under a new direction".

Helper 2, who wrote the code, is busy with two other defects of the public path (#5966, #5967). You repair your own three findings. The final independent reviews will cover your repairs, since you are now their author.

## Where you work

A new branch and worktree from the published candidate head:

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-launch-sequence-hardening-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-launch-sequence-hardening-20261112 \
  0fc003a86081891abbe8e130ac760c01da06423e
```

That head already carries helper 2's launch-sequence commits and the repair `d2efa5501`. Helper 1 keeps committing on its own branch after that head (the pending-floor repair, in `cli/receipts.py`, `native_shared_capture_orchestration.py` and `native_shared_gates.py`), and helper 2 will change the environment the controller constructs for the native process. Keep out of those files where you can, and name every file you touch so that the lead can order the integration.

## The repairs, one commit each, each with the tests your review named

1. **#5989, one start per delegated direction.** A delegated start consumes its direction once: a durable claim in registration-scoped state, independent of the packet path, bound to the direction's recorded identity and the registration digest, written before the capture command. A second sequence start that presents the same direction refuses, whatever packet directory it names. The old claim is kept. An owner start (neither delegation flag) is not limited to one, because the owner may start again under N1's line 353; it still records each start. The permanent limits-mismatch refusal stays separate and unchanged. Test: a different-packet retry after a transient capture refusal, same direction, refuses before capture; the same with a newly recorded direction is admitted.
2. **#5990, the bytes that run are the bytes that were verified.** The entry reads the sequence script's bytes once, checks them against the review bundle's `sequence_script_sha256` and the registration's source pin, executes exactly those bytes, and retains exactly those bytes in the packet. Rereading `__file__` afterwards is not a proof and is not used as one. It must not import the verifier bootstrap from inside the verified consumer (the constraint `d2efa5501` repaired). State plainly what remains trusted after the repair (the interpreter, the small entry itself) and keep that entry as small as it can be. Test: the load-A, replace-with-B witness refuses before capture.
3. **#5991, a child uses the bytes its parent checked.** The parent passes the expected digest of every input document to each child command, and the child compares the exact bytes it is about to use with that digest before any effect. Test: a replacement with another internally valid input set after the parent's check and before the child's read reaches no capture.

If a repair cannot be made without changing the kind or version of a registered document (the review bundle, the owner terms, the registration), stop before that change: write the two smallest designs and your recommendation in the handoff, and implement the one that changes no document version if there is one. Guard v1 stays byte-identical. Protected files stay equal to main.

After the three commits: run every touched test file whole, in your own scratch, and report from saved output. Then run the launch-sequence and review-bundle test files of the candidate to show nothing else moved.

## Bounds

As in the context file. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write. Helper 1's and helper 2's trees are read-only for you.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112.md` with its JSON. Answer first: the three commits, the files each touches, what stays trusted after #5990, whether any document version had to change, and the test counts. Write a first version when the first repair is committed.
