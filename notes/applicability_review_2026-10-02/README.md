# DRAFT applicability contexts for scientific review

This packet proposes seven applicability declarations for each of AI_READI,
CHORUS, CM4AI, adult VOICE, and VOICE_PEDIATRIC. Codex, an AI assistant, assembled
the packet on 2026-10-02. **No named human has reviewed or approved these drafts.**
They are not registered evaluation inputs and do not authorize scoring. Issue
[#2912](https://github.com/bridge2ai/data-sheets-schema/issues/2912) remains open.

The four new contexts were drafted from the exact repository source bundles
pinned in `review_manifest.json`. The CHORUS context is a byte-for-byte copy of
the existing ignored September 19 v2 draft. Its preserved review allowed future
context use, but identifies no reviewer and does not establish human approval.
The original ignored draft, earlier draft, evidence, and reviews remain untouched.

## Proposed declarations

`null` means unresolved and remains in the denominator. It is not an exclusion
or evidence of absence. No predicate is proposed as `false` in this packet.

| Dataset | Human subjects | Regulated access | Shared | ML training | Collection | Processing | Processing software |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AI_READI | true | true | true | null | true | true | null |
| CHORUS | true | true | true | true | true | true | true |
| CM4AI | null | true | true | true | true | true | true |
| VOICE (adult) | true | true | true | null | true | true | true |
| VOICE_PEDIATRIC | true | true | true | null | true | true | true |

The contexts contain evidence and limitations. `evidence.json` adds 33 source
passages with exact original filenames, inclusive physical **bundle** lines,
excerpt bytes/hashes, and all 35 decisions. These are not PDF page numbers.
The manifest pins each full source bundle, context bytes, normalized context
digest, the normalizer, source manifest, and the reviewed rubric/agent files.
Those rubric pins record review inputs; they do not select a future instrument.

## Decisions the scientific reviewer must resolve

1. **CM4AI scope and human subjects.** The June release explicitly says
   `Human Subjects: No` and describes commercially available de-identified human
   cell lines (`CM-governance`, `CM-cell-lines`). The bundled Nature paper's
   downstream analysis used 914 cancer patients under 25 (`CM-downstream-patients`).
   That downstream application is not the experimental release's cohort. The
   rubric's human-origin/representation meaning also need not equal a regulatory
   human-subjects label. Select the eventual record's scientific scope before
   changing `null` to true or false. The issue's shorthand “CM4AI, which is cell
   lines” is insufficient evidence for a project-wide exclusion. CM4AI processing
   and software declarations concern documented project methods; the June
   release explicitly omits computed cell maps.
2. **Training-specific use.** CHORUS's original draft uses intended model
   development; CM4AI explicitly lists intended AI model training. AI_READI and
   VOICE describe future AI/ML research, and pediatric VOICE describes developing
   AI screening tools. Those passages do not unambiguously define a training
   corpus. Decide whether intended model development qualifies, then apply the
   same interpretation to every context, including the preserved CHORUS draft.
   Workforce education, use of a pretrained extractor, and “No training required”
   in an access policy are not evidence of ML training. No draft claims a model
   was trained or a train/test split was released.
3. **AI_READI processing software.** The bundle documents REDCap range checks,
   human-guided edits, OMOP/DICOM mapping, and OMOP Data Quality Dashboard checks
   (`AI-processing`, `AI-qc-software`). Processing is clearly applicable.
   Decide whether the named checking/editing workflows establish transformation
   software, or supply a passage identifying such software. The null declaration
   does not claim that no processing software exists anywhere in the bundle.
4. **Governance semantics.** The reviewed semantic agent defines
   `regulated_access` as an applicable governance constraint. CM4AI's
   noncommercial/share-alike license and temporary embargoes support the proposed
   true declaration under that meaning. It does not assert credentialing, a
   patient-data DUA, or FDA regulation. Confirm this interpretation against the
   eventual instrument; public access does not remove a reuse restriction.
5. **Adult and pediatric separation.** Adult VOICE is anchored to v3.1's adult
   derived-feature release. Its bundle also contains a pediatric page, and the
   adult page's methods mention the broader project's pediatric group. Those
   statements do not place pediatric participants in the adult release.
   Pediatric v1.1.0 supplies its own 300-participant, ages 2–18 evidence.
   Adult b2aiprep v3.0.0 is not assigned to pediatric data. Neither PhysioNet
   derived-feature release is represented here as containing original raw audio.

## Review and identity check

From the repository root, using the project's installed environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python notes/applicability_review_2026-10-02/verify_packet.py
```

The offline verifier checks all source and artifact hashes, normalizes all five
contexts with `load_context`, checks exact predicate coverage and duplicate keys,
and checks every citation's lines and containing `FILE:` section. Its success
means that the supplied draft packet is internally consistent with its pinned
inputs. **It is not scientific review, approval, registration, or calibration.**
It makes no provider calls. For sparse clones, materialize the pinned files from
the manifest's base commit using Git; do not regenerate or replace the bundles.
The verifier reports a SHA256 of the manifest for an external review to pin.

A named human reviewer should record their identity, date, reviewed manifest
SHA256, each approved context's byte and normalized hashes, source scope, and
explicit resolution of the questions above in a new companion review. Preserve
this draft. Any changed context, source bytes, scope, predicate interpretation,
rubric, or instrument requires renewed review; prior approval must not silently
transfer to changed inputs. Independent AI checks do not fulfill human review.

## Remaining evaluation work

After human review and the semantic/Q19 instrument decision, a separate opt-in
registration must bind accepted record identities and original source bundles
to the reviewed contexts. These current canonical bundles do not prove that an
older record used the same source bytes. Context reuse across Dataset/CoreDataset
also requires the same scientific scope, not just the same project label.

The new roster must add at least two extra rubric20 ratings per project, include
CM4AI v7 rep2, and verify an eligible pediatric record rather than infer one from
the historical 24-record roster. A pediatric source bundle alone is not an
accepted record. Keep the frozen 56-job roster and v1.x results unchanged; report
new results separately by evaluator, instrument, and context. Excluded-item
identities and stability remain unmeasured until an accepted complete panel.
A separately authorized CM4AI canary must precede any paid fill. This packet
creates neither a roster nor a canary and does not modify held audit28 inputs.

## Discovery limits

The preparation searched YAML/YML/JSON content with `rg --no-ignore --hidden`
under the primary checkout's `notes`, `data`, and `docs`, including nested ignored
local worktrees. It found and preserved the CHORUS drafts plus the existing
kids_first and external_clinical contexts. The manifest records the command and
scope. The 12,573 matching files include many evaluation/request documents;
they were discovery candidates, not 12,573 reviewed contexts. Sibling execution
worktrees, other `/tmp` clones, binary files, and differently formatted contexts
were not exhaustively searched. No claim of global context absence is made.
