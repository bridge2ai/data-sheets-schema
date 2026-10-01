# Q19 recommendations: a blind second reading and its agreement (2026-09-30)

Issues #3831 and #3871. The 122 sentences a leading-verb regex sorts among the
recommendations (#3747) were classed by the ordered test in the module
docstring of `src/data_sheets_schema/q19_rationale_lint.py`, and each is pinned
to its class by a fragment in `tests/test_q19_rationale_lint.py`
(`_RECOMMENDATIONS_READ`). Those pins are the **first reading**. This note
compares them with a **second reading** of the same 122.

## What was read, and by whom

| file | what it is | sha256 |
|---|---|---|
| `notes/q19_recommendations_3831_packet.json` | the 122 sentences, each with its source rating file and JSON path; no classes | `9a9b0dec8b2053c89de776d76273517108224885fd5073a26834d7b1ceb9152d` |
| `notes/q19_recommendations_3831_rubric.md` | the docstring's ordered test, with every example sentence, per-class count and pinned sentence removed | `905b5cb72472d36bcfc706fdbbcfd8cad903908a6073aa849f482180fb732791` |
| `notes/q19_recommendations_3831_first_reading.yaml` | the pins at origin/main c962a6cc8 in per-item form; a test checks it against the pins | |
| `notes/q19_recommendations_3831_second_reading.yaml` | the second reading, class, `unsure` and reason per item, verbatim from the reader's JSON | JSON `004fb984cc8f4e762e390e82ec7660d5b550403e3ffdcf5e20ba72c41ec0e741` |

The second reader was a separately run Claude agent given only the packet and
the rubric. It did not see the pins, the module docstring, the test file or the
first reading. It is **a second model reading, not an independent human
rater**. Both readers are model agents, so agreement between them does not
establish what a human reader would conclude.

One limit of this reading matters for step 3. On ten items the reader's reason
says the rating was "not visible" or "not checked", and none of its reasons
quotes a rating. Step 3b asks whether the sentence's own rating faults the
value, so the second reader's step 3 versus step 4 calls rest on the sentence
alone. Steps 1 and 2 do not need the rating. They decide the miss count #3544
uses, and the second reading tests them fully.

## Figures

Everything between the markers is written by `scripts/q19_blind_agreement.py`
from the two YAML files. `tests/test_q19_blind_second_reading.py` recomputes it
and fails if it differs. Kappa is Cohen's, with the Fleiss, Cohen and Everitt
(1969) large-sample standard error. With one disagreement in 122, the Wald
interval for steps 1-2 is a rough guide only.

<!-- BEGIN GENERATED: scripts/q19_blind_agreement.py -->

- All four classes: 0.910 raw (111/122); kappa 0.847 (95% Wald CI 0.766 to 0.929; chance agreement 0.409).
- Steps 1-2 (miss = named_absence or placement, versus not): 0.992 raw (121/122); kappa 0.984 (95% Wald CI 0.951 to 1.000, the Wald bound 1.016 truncated; chance agreement 0.502).
- Step 3 versus 4, over the items both readings take past steps 1-2: 0.825 raw (47/57); kappa 0.539 (95% Wald CI 0.301 to 0.777; chance agreement 0.620).
- Disagreements: 11; the second reader marked 6 of them unsure (29 unsure of 122 in all).

Confusion matrix (rows: first reading; columns: second):

| first \ second | named_absence | placement | criticism | request | total |
|---|---:|---:|---:|---:|---:|
| named_absence | 1 | 0 | 0 | 0 | 1 |
| placement | 0 | 63 | 0 | 0 | 63 |
| criticism | 0 | 0 | 9 | 9 | 18 |
| request | 0 | 1 | 1 | 38 | 40 |
| total | 1 | 64 | 10 | 47 | 122 |

Agreement by class (specific agreement = 2 x both / (first + second)):

| class | first | second | both | specific agreement |
|---|---:|---:|---:|---:|
| named_absence | 1 | 1 | 1 | 1.000 |
| placement | 63 | 64 | 63 | 0.992 |
| criticism | 18 | 10 | 9 | 0.643 |
| request | 40 | 47 | 38 | 0.874 |

Sensitivity, not a change (the pins, the module docstring's counts and the lint are as on main):

- Q19 misses among the 122: 64 under the first reading, 65 under the second (+1).
- Misses among the 277 hand-read sentences (#3544): 95/277 under the first reading, 96/277 with the second reading's 122 (31 outside the 122 held fixed).

Every disagreement:

### q19r-001: criticism (first) / request (second)

> Add a was_derived_from link to the raw audio Synapse resource and, when available, a publication DOI and a conflicts-of-interest statement under ethical_reviews

Source: `data/evaluation_llm/rubric10_semantic/label_aware/VOICE_2026-08-28agentic_rep3_evaluation.json` `/assessment/recommendations/4`

- First, criticism (comment): ethical_reviews holds the USF IRB and Canadian REB reviews, and the rating's note on it says "no conflicts-of-interest statement"
- Second, request: imperative to add was_derived_from; no absence, placement or objection stated

### q19r-006: request (first) / placement (second)

> Add parent_datasets/was_derived_from pointing to doi:10.60775/fairhub.2 and an errata entry, and consider embedding the RO-Crate lineage as a provenance graph

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-08-22c_rep2_evaluation.json` `/assessment/recommendations/2`

- First, request (comment): "consider embedding the RO-Crate lineage as a provenance graph" asks for a change to a release artifact the record points at, not to a value the record holds; it gives the slots' content as doi:10.60775/fairhub.2 and the lineage a graph of its own. Round 4 (#3836): "the RO-Crate lineage" is to become a graph of its own, not what the parent_datasets/was_derived_from it asks for are to hold
- Second, placement (unsure): points to the RO-Crate lineage (a file) as where the lineage is; weak placement

### q19r-011: criticism (first) / request (second)

> Add tool versions (b2aiprep, openSMILE, sparc, ppgs, Whisper), populate publisher and was_derived_from, and cite the feasibility publication and white paper with DOIs in external_resources.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/superseded_fable5/VOICE_2026-09-01api_rep1_evaluation.json` `/assessment/recommendations/4`

- First, criticism (comment): preprocessing_strategies names b2aiprep, openSMILE, sparc, ppgs and Whisper, which the rating says carry no version ("No tool carries a version number"), and external_resources, which it faults for not listing the feasibility publication and white paper
- Second, request (unsure): requests; 'add tool versions' may be more-on-held-entries criticism but rating not visible

### q19r-013: criticism (first) / request (second)

> Add versions and URLs for sparc, openSMILE, Praat, Parselmouth, ppgs and Whisper; populate conforms_to_schema and a was_derived_from link to the raw audio source.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/VOICE_2026-08-28agentic_rep1_evaluation.json` `/assessment/recommendations/4`

- First, criticism (comment): preprocessing_strategies and machine_annotation_tools name sparc, openSMILE, Praat, Parselmouth, ppgs and Whisper, which "have neither version nor URL"
- Second, request (unsure): requests; versions/URLs for tools may be criticism of held entries, rating not visible

### q19r-050: criticism (first) / request (second)

> Mirror the version lineage into was_derived_from and parent_datasets, and attribute the disclosed 419,614-byte residual so both provenance and size arithmetic are machine-checkable in the slots consumers query.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v7_rep3_r20_rating1_evaluation.json` `/assessment/recommendations/7`

- First, criticism (comment): source_caveats discloses the 419,614-byte residual, which the rating calls "stated but unexplained"
- Second, request (unsure): mirror lineage (no location); 'attribute the residual' may be criticism, rating not visible

### q19r-065: criticism (first) / request (second)

> Populate parent_datasets with doi:10.60775/fairhub.2 and set was_derived_from to the same identifier, keeping the study-name prose in notes.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-09-04gapi_rep2_evaluation.json` `/semantic_analysis/issues_detected/2/recommendation`

- First, criticism (comment): was_derived_from holds the study's name in prose, as its rating's own evidence quotes; "keeping the study-name prose in notes" says where content is to go (the value was_derived_from holds, moving to notes), not where a slot's content is now
- Second, request (unsure): request; notes mention concerns study-name prose, not the slot's content

### q19r-092: criticism (first) / request (second)

> Populate was_derived_from and parent_datasets so each processed archive links to its raw source, and name the archive carrying the RO-Crate descriptor and provenance graph so the FAIRSCAPE claim can be verified.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v8_rep1_r20_rating1_evaluation.json` `/assessment/recommendations/3`

- First, criticism (comment): file_collections lists ten archives and conforms_to claims an RO-Crate provenance graph, and the rating says no listed archive is stated to carry it
- Second, request: request; no current location stated

### q19r-093: criticism (first) / request (second)

> Populate was_derived_from and parent_datasets so the derivation path is machine-readable, and add file_collections with byte totals and file counts alongside an expanded variables list covering the principal phenotype columns.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v7_rep1_r20_rating1_evaluation.json` `/assessment/recommendations/4`

- First, criticism (comment): variables holds four columns ("enumerates only four columns")
- Second, request: plain requests

### q19r-115: request (first) / criticism (second)

> Record the publisher as a URI (https://fairhub.io) so Q13 sustainability consumers can find the repository in the structured slot.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-08-28dapi_rep1_evaluation.json` `/semantic_analysis/issues_detected/12/recommendation`

- First, request (reconstructed): no comment names this pin; its rating (issues_detected[12]) says "publisher is absent", so the sentence names no value the record holds and step 3a fails: a request
- Second, criticism (unsure): asks held publisher to be a URI instead; rating not checked

### q19r-118: criticism (first) / request (second)

> State character encoding (presumably UTF-8) on the text formats and add a was_derived_from statement summarising the raw-to-release derivation.

Source: `data/evaluation_llm/rubric10_semantic/reference_2026-09-11/AI_READI_v7_rep1_r10_rating3_evaluation.json` `/semantic_analysis/issues_detected/8/recommendation`

- First, criticism (comment): the text formats are listed with no encoding, which the rating records as a warning
- Second, request: plain request

### q19r-121: criticism (first) / request (second)

> Wire the provenance explicitly: give each file_collection a was_generated_by link to the acquisition or preprocessing activity that produced it, and state whether the shipped RO-Crate provenance graphs carry per-modality processing parameters.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v7_rep2_r20_rating1_evaluation.json` `/assessment/recommendations/8`

- First, criticism (comment): file_collections lists ten collections, and the rating says "no collection carries a was_generated_by"
- Second, request: request to add was_generated_by

<!-- END GENERATED -->

## Reading the disagreements

- **Steps 1-2 (the misses).** The readings differ on one item, `q19r-006`. The
  first reading classes it as a request and the second as a placement. Its
  rating says lineage "is recoverable from prose, and the RO-Crate is
  referenced". The sentence asks to "consider embedding the RO-Crate lineage as
  a provenance graph". The first reading takes the RO-Crate to be a release
  artifact and the requested graph to be content of its own. The second takes
  "the RO-Crate lineage" to say where derivation content already sits, in a
  file. The rubric counts a file as a placement. It also says a release
  artifact is not a value the record holds, but it says that in step 3a, which
  a placement never reaches. Filed as a follow-up for adjudication, not changed
  here.
- **Step 3 versus 4.** On nine items the first reading says criticism and the
  second says request. In every one of them, the first reading's reason quotes
  the item's own rating faulting a populated value. The second reader did not
  consult the ratings, so these disagreements come from step 3b not being
  applied. They do not show an error in the first reading. Spot checks of the
  nine source ratings found each quoted fault: "no conflicts-of-interest
  statement", "have neither version nor URL", "stated but unexplained",
  "enumerates only four columns", "no collection carries a was_generated_by",
  and so on.
- **`q19r-115`** goes the other way: the first reading says request and the
  second says criticism. The second reader read "Record the publisher as a URI"
  as an objection to a held publisher. The item's rating says "publisher is
  absent", so no populated value is named and step 3a fails. The first reading
  stands. No pin comment gives this reason. The integrating agent reconstructed
  it from the rating, and the first-reading file marks it `basis:
  reconstructed`.

Nothing here changes a pin, a class, the module docstring's counts or the
lint. The second reading would move the Q19 miss count by one: 64 to 65 among
the 122, and 95 to 96 of the 277. That holds only if `q19r-006` is a placement,
which is the open question above. #3544 reports the 95 as a count, not a recall
ratio, so no precision or recall figure moves.
