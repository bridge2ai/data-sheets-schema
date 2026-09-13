# Manifest-owned corpus roots — 2026-09-13

Issue #1523 completes the external-project path from the profiles and
packaging stages. A conventional source manifest owns its project root;
standalone manifests own their containing directory. Registry bundle/source
paths, chunk mappings, conventional run outputs, receipts, provenance,
run discovery, canonical selection, review-pack inputs and corpus scans use
that same root. Explicit output-directory overrides remain caller-relative.
A caller without a selected manifest does not write into the imported
checkout. Implicit discovery within the checkout retains its main manifest
so archived copies do not silently change the active project.

The generation/evaluation reference artifacts and frozen prompt files are
unchanged. Existing recorded render specs keep their recorded paths and
renderer semantics. New runs use the selected corpus locations. This is a
path-selection boundary, not a new measurement: no production record was
generated or rescored, no definition was quoted by a new evaluator, and no
source download occurred. Both agentic and API arms remain in the overall
completion plan. Evaluation coverage remains presence, API judging, semantic
agent output acceptance, deterministic checks and semantic pair review.

Validation: the initial 100 routing/profile/API checks pass; the broadened
output-guard and CLI/review-pack lanes pass 84 and 65 checks. The final corpus
consumer lane passes 277 tests, plus its corrected Click-context fixture
passes separately. A clean wheel installs with only runtime dependencies:
the six existing acceptance checks pass, and the new ancestor-manifest
acceptance passes after correcting tuple unpacking in its fixture. It creates
chunks, executes the real API runner with a fake client, derives and validates
the pair, discovers both runs and passes strict run/provenance checks from a
nested external directory. Synthetic archive planning remains read-only.

The remaining installed-agentic command and transcript-helper work is #1556.
Independent review and exact-head CI are required before merge.

## Review round 2 — 2026-09-13

The independent review produced #1594–#1598; the adjacent explicit root/
environment-selection mismatch is #1601. Automatic discovery outside the
checkout now selects only the caller's manifest, so a checkout fallback
cannot acquire output ownership. Explicit --manifest and D4D_MANIFEST
selections govern API context and profile defaults; a command's own explicit
path or none takes precedence. Relative caller input paths are captured as
absolute when they cross into another manifest's output tree. Default
provenance outputs follow that tree, including programmatic recording.

Artifact-pin verification resolves against the same corpus. A modified
artifact reports stale; an unavailable pinned artifact reports unverified.
Programmatic selected manifests now govern chunk discovery directly for
agentic and receipt-condition API specs. Renderer 5 records full/core/report/
receipt destinations and substitutes them into the actual output instructions.
Versions 1–4 remain replayable: all 48 historical controls match byte hashes.
Backfill includes renderer 5, but still writes only after exact hash matching.

Nine regression cases fail before these fixes. The compatibility lane passes
222 tests before updating the old outside-checkout profile expectation; the
final nine review guards and that expectation pass all 10 checks. The runner/
record lane passes 174 tests before adding renderer 5 to backfill; the complete
backfill test then passes. The actual wheel passes all seven release checks.
The preservation audit verifies 56 existing ratings and all 450 hashes.
Additional root/environment selection and installed plan checks follow the
same controls. No new production generation, scoring or source downloads.

The additional context/profile/rendering lane passes 70 tests. A fresh-wheel
check of global CLI/environment selection is running on the same source.

## Review round 3 — 2026-09-13

The four round-2 findings are #1602–#1605. Artifact verification and validation
preservation now follow the provenance record's own corpus, including an
explicit corpus that differs from the launch directory's ancestor manifest.
The strict provenance gate uses the same owner. Explicit no-manifest recording
keeps caller outputs; a context-unused arm's CLI recorder passes its selected
output tree independently of whether manifest context was consumed. Renderer 5
receipt commands always bind that selection, including explicit none. Backfill
uses recorded output destinations and canonical ordering, still requiring the
complete original request SHA256 before writing.

Nine synthetic cases reproduce these faults at the reviewed head; the final
eleven targeted checks pass. The broader provenance lane passes 171 checks
before the last backfill ordering fix, and that corrected recovery passes in
the final targeted lane. The selected generation/replay lane passes 62 checks.
All 48 historical renderer 1–4 controls remain byte-identical. All seven
fresh-wheel acceptance checks pass (107.19 seconds). No production
record, rating, instrument attribution or source bundle was modified.

After integrating published profile/packaging head 805ff3eb and the installed
workflow's validation note, all 101 combined corpus/profile/recording checks
pass. Backfill retains both recorded profile selection and output destinations.
The implementation JSON is refreshed for this combined tree; independent
review and CI will use the committed head.

## Review round 4 — 2026-09-13

The round-3 review found #1613 and #1614. Explicit output overrides now freeze
their caller-owned absolute paths when a run is specified. Conventional
corpus-relative pins retain their corpus owner; old absolute flat record
addresses do not guess an unrecorded base for relative pins. This prevents an
ancestor project's duplicate output from hiding drift in the actual output.
The recorder preserves conventional relative destinations when launched at
the project root. Hash-only backfill also tries a corpus-relative spelling of
recorded absolute destinations, still writing only when the original complete
request hash matches.

Five synthetic cases fail at the prior head. All 53 targeted corpus/CLI checks
pass after the fix; the broader generation, provenance, recovery and usage
lane passes 331 tests. All seven fresh-wheel checks pass, including an actual
API run with a caller-relative flat output override under an ancestor manifest.
All 60 renderer 1–5 controls remain unchanged. CI on the previous head had one
legacy fixture failure and 4367 passes: #1615 updates that fixture to select
its study manifest and chunk directory explicitly from an external cwd,
retaining the original chunk-identity assertion without reinstating imported
checkout ownership. The dated implementation pins are refreshed.

No production input, output, rating or historical attribution was rewritten.
The next independent review and exact-head CI remain merge gates.

## Review round 5 — 2026-09-13

The round-4 findings are #1644 and #1645. Conventional record ownership now
requires the actual method_core/label/provenance layout and corpus-relative
artifact pins. A legacy flat override nested below data/d4d_concatenated
cannot acquire an ancestor's duplicate files. Unknown absolute flat-record
bases remain unverifiable. Chunk discovery and chunk-name validation now
receive the same selected source-manifest namespace. Recording keeps that
namespace separate from consumed context, including crate-only and
healthsheet arms whose source-manifest context is unused.

All six original reproductions fail before the fixes. The expanded corpus,
chunk, manifest-identity, backfill and pair-gate lane passes 85 checks,
including consumed and unused context with selected symlink aliases. The CI
fixture correction is #1646: an in-memory copy of a historical provenance
record now keeps its original artifact locations when moved outside its
corpus. The historical on-disk record is unchanged.

All seven fresh-wheel workflows pass on these fixes (122.21 seconds), with
only declared runtime dependencies and fake-provider fixtures. All 60
historical renderer controls match. The read-only preservation audit verifies
56 accepted ratings, 259 prior evaluations and 450 preservation hashes.
The next independent review and exact-head CI remain required before merge.

## Review round 6 — 2026-09-13

The round-5 findings are #1649–#1651. Output artifact verification follows
the record before considering resource namespaces, so a deleted flat output
under project/ cannot verify through a package copy. New agentic specs record
chunk_check_uses_manifest and emit bundle chunk's own selected --manifest
option, including explicit none. Older saved specs omit that switch and
retain their original command bytes. Backfill tries both forms and both
relative and owner-anchored destinations, writing only after the complete
original instruction hash matches.

The expanded corpus/backfill/replay lane passes 66 tests; the emitted-command
and remaining prompt-consumer lane passes 100 tests. The cross-directory
fixture captures its chunk path before changing directory. All 60 historical
renderer controls remain unchanged. Prior-head CI had exactly the copied
pair-gate fixture failure already fixed by #1646, with 4406 passes and 13
skips. No measured record, rating or original working-tree file was changed.

## Final dependency integration and round 7 — 2026-09-13

The branch now includes the published profile and packaging fixes through
installed-workflow dependency 66130d5cb. #1653 separates omitted source-manifest
selection from explicit none in chunk discovery, canonical names, API phase
assembly and recorded chunk identity. An automatically undeclared project
uses the caller's sidecar even when its bundle is a symlink into an ancestor
corpus. Its emitted strict preflight now validates the same selection.

The emitted-command regression fails before the fix. All 76 focused checks
pass, followed by 177 combined profile/resource/corpus/replay checks with one
existing skip. All eight fresh-wheel workflows pass (125.60 seconds), and all
42 frozen-controller/audit checks pass. All 60 historical renderer controls
retain their hashes. The nested archived-checkout probe also confirms resource
and corpus discovery agree after the upstream integration. No production
record, prior score or historical instrument attribution is rewritten.
The next review and CI use this combined committed implementation.

## Review round 8 and dependency integration — 2026-09-13

#1675 fixes validation from a nested directory. The runs command now keeps
the corpus it discovered and validates explicit full/core paths, without
constructing a generation spec that could select a different manifest. The
verdict and hashes describe that same discovered pair. Four regressions cover
new and replacement verdicts, with and without invalid caller-local copies;
they fail before the fix and pass afterward, preserving recorded hash algorithms.

All 55 focused validation/recheck checks pass, followed by 156 run-selection
and compatibility checks. The combined tree includes profile 6a35a45ee,
packaging 8c48a532b, and installed-workflow c94059d7e, including the wrapper
shebang correction. All 101 corpus/selected-command/recording integration
checks pass. All 60 historical renderer controls retain their hashes.
The next independent review and exact-head CI remain merge gates.
No production record, rating, source bundle or historical attribution changes.

## Review round 9 — 2026-09-13

#1689 binds provenance rechecks to the discovered record's corpus and requires
the replacement hashes to equal the prior pins under every recorded algorithm.
Unavailable prior pins hold the bulk update. Equivalent problem-path spellings
are compared only after their artifact hashes reproduce. #1690 preserves any
existing validation verdict during default runs validate, including a relocated
record whose old absolute paths are unavailable; --recheck remains explicit.

All six original regressions fail before the fixes. The expanded lane passes
63 validation, guarded-recheck and preservation checks, including unavailable
pins and equivalent relative/absolute problem paths. Older gate fixtures now
compute actual artifact hashes instead of returning placeholder values. All
223 broader corpus/run checks pass and all 60 renderer controls match. #1688
keeps the implicit chunk-write guard fixture in its own synthetic manifest.
The branch includes installed dependency a18659192 and packaging 2a840076a.
No production artifact, score or historical attribution changes; the next
independent review and exact-head CI remain required.

## Review round 10 — 2026-09-13

#1693 binds a review pack's bundle and chunk map to the provenance record's
corpus before loading evidence. Resolved bundle paths also reach receipt and
snippet checks. An absolute legacy flat record with relative inputs and no
established base reports a gap; a caller's same-named files are never used
as substitute evidence. Five nested/unrelated-caller regressions fail before
the fix, with missing or conflicting local maps and an unknown legacy base.

All 65 focused review-pack/disposition checks pass. The combined corpus,
selected-command and latest profile lane passes 164 checks. The installed
agentic integration passes its 25 review-pack/identity checks. This tree also
retains the profile27b627fa2 compatibility fixes, with explicit ValidationInputs
for validation and the complete corpus destination/backfill candidate set.
The next independent review and exact-head CI remain required. Existing
production records, ratings and historical attributions are unchanged.

## Review round 11 — 2026-09-13

Codex round 10 found #1695 and #1696. Canonical full/core paths now resolve
from each provenance record's corpus; unknown relative bases are unavailable.
New flat-output provenance captures bundle, chunk-map and source-manifest
addresses while the launch directory is known, so later review retains its
evidence. Historical flat records with unknown bases still remain unverified.

Seven regression cases fail before the fix. The focused canonical/planning/
review lane passes 111 tests, and all corpus/recheck/backfill/selection checks
pass 185 tests. After integrating #1694 from 8dec686e5, the eleven combined
regressions pass. All 60 historical renderer controls retain identical bytes.
The boundary refreshes the affected source pins and names the integrated
validator dependency. No production generation, scoring or downloads occur.

## Review round 12 — 2026-09-13

Round 11 confirmed canonical planning and found #1724–#1726. Automatic
selection now precedes output ownership; header-only reconstruction uses its
discovered owner and retains explicit manifest overrides. A different output
owner makes new input addresses absolute, including flat destinations that
resemble another corpus. Backfill and review share a recorded-input resolver.
Unknown relative bases cannot borrow caller bundles or chunk maps. Receipt
recovery remains available when recorded hashes and rules establish it.

Eight initial ownership cases fail before the correction. The focused
receipt/backfill lane passes 96 tests; the explicit-manifest compatibility
case is then added and corrected, and the broader corpus/receipt/review lane
passes 223 tests. Profile 9671c91e9, packaging c50d65508 and validator #1713
are integrated through 1e50aa0e7. Their combined checks pass 185 tests with
one existing skip and one fixture failure; #1731 gives that fixture its own
dataset, and its targeted check passes. All 60 historical renderer controls
remain identical. The boundary now pins 17 source files. No production
generation, scoring, downloads or historical artifact rewrites occur.
