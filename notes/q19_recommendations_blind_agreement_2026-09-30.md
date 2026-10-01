# Q19 recommendations: a blind second reading and its agreement (2026-09-30)

Issues #3831 and #3871. The 122 sentences a leading-verb regex sorts among the
recommendations (#3747) were classed by the ordered test in the module
docstring of `src/data_sheets_schema/q19_rationale_lint.py`, and each is pinned
to its class by a fragment in `tests/test_q19_rationale_lint.py`
(`_RECOMMENDATIONS_READ`). Those pins are the **first reading**. This note
compares them with a **second reading** of the same 122.

There are two blind second readings. The **reading of record** was made with
the rating files that rubric step 3b asks about. An earlier reading was made
without them, because its reader's instructions forbade opening those files.
That earlier reading could not apply step 3b. It is kept as a **recorded
deviation**, and its figures are reported below, not discarded.

## What was read, and by whom

| file | what it is | sha256 |
|---|---|---|
| `notes/q19_recommendations_3831_packet.json` | the 122 sentences, each with its source rating file and JSON path; no classes | `9a9b0dec8b2053c89de776d76273517108224885fd5073a26834d7b1ceb9152d` |
| `notes/q19_recommendations_3831_rubric.md` | the docstring's ordered test, with every example sentence, per-class count and pinned sentence removed | `905b5cb72472d36bcfc706fdbbcfd8cad903908a6073aa849f482180fb732791` |
| `notes/q19_recommendations_3831_first_reading.yaml` | the pins at origin/main c962a6cc8 in per-item form; a test checks it against the pins | |
| `notes/q19_recommendations_3831_second_reading.yaml` | **the second reading of record**, made with the step 3b sources: class, `unsure` and reason per item, verbatim from the reader's JSON | JSON `e34907ebc915b7809f342a9e86b2895a2cd0bf43dc7e57f184e9d86d0ebd4138` |
| `notes/q19_recommendations_3831_second_reading_without_sources.yaml` | the earlier reading made without the step 3b sources, a recorded deviation; judgements unchanged from 89101b256 | JSON `004fb984cc8f4e762e390e82ec7660d5b550403e3ffdcf5e20ba72c41ec0e741` |

Both second readers were separately run Claude agents. Each was given the
packet and the rubric, the same bytes both times. The reader of record was
also given the 84 rating files the packet's 124 sources name, copied at the
same relative paths. Each copy was compared with this checkout's file and is
byte-identical. Those files carry the ratings' weaknesses, issues and quality
notes, and no first-reader class.

Neither reader saw the pins, the module docstring, the test file or the first
reading. That rests on how they were launched and on their own reports; no
file here can prove it. The reader of record reports that it pulled the
matching weaknesses, issues and quality notes out of each rating with a small
text-extraction script, and that it made every class decision itself. Each is
**a second model reading, not an independent human rater**. All three readers
are model agents, so agreement between them does not establish what a human
reader would conclude.

## Figures

Everything between the markers is written by `scripts/q19_blind_agreement.py`
from the three YAML files. `tests/test_q19_blind_second_reading.py` recomputes
it and fails if it differs. Kappa is Cohen's, with the Fleiss, Cohen and
Everitt (1969) large-sample standard error. Where an interval reaches 1, the
Wald bound is truncated and the interval is a rough guide only; with one to
three disagreements in 122, the normal approximation is poor.

<!-- BEGIN GENERATED: scripts/q19_blind_agreement.py -->

### The second reading of record (with the step 3b sources) against the first

- All four classes: 0.975 raw (119/122); kappa 0.959 (95% Wald CI 0.914 to 1.000, the Wald bound 1.005 truncated; chance agreement 0.397).
- Steps 1-2 (miss = named_absence or placement, versus not): 0.992 raw (121/122); kappa 0.984 (95% Wald CI 0.952 to 1.000, the Wald bound 1.016 truncated; chance agreement 0.501).
- Step 3 versus 4, over the items both readings take past steps 1-2: 0.966 raw (56/58); kappa 0.917 (95% Wald CI 0.804 to 1.000, the Wald bound 1.030 truncated; chance agreement 0.585).

Confusion matrix (rows: first reading; columns: second):

| first reading \ second | named_absence | placement | criticism | request | total |
|---|---:|---:|---:|---:|---:|
| named_absence | 1 | 0 | 0 | 0 | 1 |
| placement | 0 | 62 | 0 | 1 | 63 |
| criticism | 0 | 0 | 16 | 2 | 18 |
| request | 0 | 0 | 0 | 40 | 40 |
| total | 1 | 62 | 16 | 43 | 122 |

Disagreements: 3; the second reader marked 2 of them unsure (24 unsure of 122 in all).

Agreement by class (specific agreement = 2 x both / (first + second)):

| class | first | second | both | specific agreement |
|---|---:|---:|---:|---:|
| named_absence | 1 | 1 | 1 | 1.000 |
| placement | 63 | 62 | 62 | 0.992 |
| criticism | 18 | 16 | 16 | 0.941 |
| request | 40 | 43 | 40 | 0.964 |

Sensitivity, not a change (the pins, the module docstring's counts and the lint are as on main):

- Q19 misses among the 122: 64 under the first reading, 63 under the second (-1).
- Misses among the 277 hand-read sentences (#3544): 95/277 under the first reading, 94/277 with the second reading's 122 (31 outside the 122 held fixed).

Every disagreement:

#### q19r-092: criticism (first) / request (second)

> Populate was_derived_from and parent_datasets so each processed archive links to its raw source, and name the archive carrying the RO-Crate descriptor and provenance graph so the FAIRSCAPE claim can be verified.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v8_rep1_r20_rating1_evaluation.json` `/assessment/recommendations/3`

- First, criticism (comment): file_collections lists ten archives and conforms_to claims an RO-Crate provenance graph, and the rating says no listed archive is stated to carry it
- Second, request (unsure): Request for provenance slots; naming the RO-Crate archive is about a release artifact.

#### q19r-114: placement (first) / request (second)

> Record the June 2025 revision and post-publication file additions as errata entries, and consider expressing the FAIRSCAPE provenance lineage as was_derived_from/parent_datasets links in the record itself.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/superseded_fable5/CM4AI_2026-09-01api_rep2_evaluation.json` `/assessment/recommendations/3`

- First, placement (comment): the comment on the two pins after it ("Beside the imperative these say the derivation provenance is already in the RO-Crate/FAIRscape package shipped with the release, a file, as the FAIRSCAPE sentence above does") names this sentence: "the FAIRSCAPE provenance lineage" is where the lineage is now, a file, which was_derived_from/parent_datasets are to express "in the record itself". Added on 2026-09-30 by the agent integrating #3831, not the pin's: its rating's weaknesses[3] says the graphs "exist only inside the RO-Crate metadata archive"
- Second, request (unsure): Requests errata and provenance links; FAIRSCAPE not clearly a location in the record.

#### q19r-121: criticism (first) / request (second)

> Wire the provenance explicitly: give each file_collection a was_generated_by link to the acquisition or preprocessing activity that produced it, and state whether the shipped RO-Crate provenance graphs carry per-modality processing parameters.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v7_rep2_r20_rating1_evaluation.json` `/assessment/recommendations/8`

- First, criticism (comment): file_collections lists ten collections, and the rating says "no collection carries a was_generated_by"
- Second, request: Request for was_generated_by; RO-Crate is not a held value.

### The reading made without the step 3b sources (a recorded deviation) against the first

- All four classes: 0.910 raw (111/122); kappa 0.847 (95% Wald CI 0.766 to 0.929; chance agreement 0.409).
- Steps 1-2 (miss = named_absence or placement, versus not): 0.992 raw (121/122); kappa 0.984 (95% Wald CI 0.951 to 1.000, the Wald bound 1.016 truncated; chance agreement 0.502).
- Step 3 versus 4, over the items both readings take past steps 1-2: 0.825 raw (47/57); kappa 0.539 (95% Wald CI 0.301 to 0.777; chance agreement 0.620).

Confusion matrix (rows: first reading; columns: without sources):

| first reading \ without sources | named_absence | placement | criticism | request | total |
|---|---:|---:|---:|---:|---:|
| named_absence | 1 | 0 | 0 | 0 | 1 |
| placement | 0 | 63 | 0 | 0 | 63 |
| criticism | 0 | 0 | 9 | 9 | 18 |
| request | 0 | 1 | 1 | 38 | 40 |
| total | 1 | 64 | 10 | 47 | 122 |

Disagreements: 11; marked unsure 6 (29 unsure of 122 in all). Q19 misses among the 122: 64 under the first reading, 65 under this one (+1).

| item | first | without sources | its reason |
|---|---|---|---|
| q19r-001 | criticism | request | imperative to add was_derived_from; no absence, placement or objection stated |
| q19r-006 | request | placement (unsure) | points to the RO-Crate lineage (a file) as where the lineage is; weak placement |
| q19r-011 | criticism | request (unsure) | requests; 'add tool versions' may be more-on-held-entries criticism but rating not visible |
| q19r-013 | criticism | request (unsure) | requests; versions/URLs for tools may be criticism of held entries, rating not visible |
| q19r-050 | criticism | request (unsure) | mirror lineage (no location); 'attribute the residual' may be criticism, rating not visible |
| q19r-065 | criticism | request (unsure) | request; notes mention concerns study-name prose, not the slot's content |
| q19r-092 | criticism | request | request; no current location stated |
| q19r-093 | criticism | request | plain requests |
| q19r-115 | request | criticism (unsure) | asks held publisher to be a URI instead; rating not checked |
| q19r-118 | criticism | request | plain request |
| q19r-121 | criticism | request | request to add was_generated_by |

### The two second readings against each other (what step 3b changed)

- All four classes: 0.918 raw (112/122); kappa 0.860 (95% Wald CI 0.780 to 0.940; chance agreement 0.413).
- Steps 1-2 (miss = named_absence or placement, versus not): 0.984 raw (120/122); kappa 0.967 (95% Wald CI 0.922 to 1.000, the Wald bound 1.012 truncated; chance agreement 0.501).
- Step 3 versus 4, over the items both readings take past steps 1-2: 0.860 raw (49/57); kappa 0.608 (95% Wald CI 0.370 to 0.846; chance agreement 0.642).

Confusion matrix (rows: without sources; columns: with sources):

| without sources \ with sources | named_absence | placement | criticism | request | total |
|---|---:|---:|---:|---:|---:|
| named_absence | 1 | 0 | 0 | 0 | 1 |
| placement | 0 | 62 | 0 | 2 | 64 |
| criticism | 0 | 0 | 9 | 1 | 10 |
| request | 0 | 0 | 7 | 40 | 47 |
| total | 1 | 62 | 16 | 43 | 122 |

Items the two second readings class differently: 10.

#### q19r-001: request (without) / criticism (with); first criticism, now agrees with the first

> Add a was_derived_from link to the raw audio Synapse resource and, when available, a publication DOI and a conflicts-of-interest statement under ethical_reviews

Source: `data/evaluation_llm/rubric10_semantic/label_aware/VOICE_2026-08-28agentic_rep3_evaluation.json` `/assessment/recommendations/4`

- Without sources, request: imperative to add was_derived_from; no absence, placement or objection stated
- With sources, criticism (unsure): Asks for more on populated ethical_reviews (COI statement); rating faults the missing COI statement.

#### q19r-006: placement (without) / request (with); first request, now agrees with the first

> Add parent_datasets/was_derived_from pointing to doi:10.60775/fairhub.2 and an errata entry, and consider embedding the RO-Crate lineage as a provenance graph

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-08-22c_rep2_evaluation.json` `/assessment/recommendations/2`

- Without sources, placement (unsure): points to the RO-Crate lineage (a file) as where the lineage is; weak placement
- With sources, request: Imperative to add parent_datasets/was_derived_from; no location stated.

#### q19r-011: request (without) / criticism (with); first criticism, now agrees with the first

> Add tool versions (b2aiprep, openSMILE, sparc, ppgs, Whisper), populate publisher and was_derived_from, and cite the feasibility publication and white paper with DOIs in external_resources.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/superseded_fable5/VOICE_2026-09-01api_rep1_evaluation.json` `/assessment/recommendations/4`

- Without sources, request (unsure): requests; 'add tool versions' may be more-on-held-entries criticism but rating not visible
- With sources, criticism: Names the held tools and asks for versions; rating faults them as versionless.

#### q19r-013: request (without) / criticism (with); first criticism, now agrees with the first

> Add versions and URLs for sparc, openSMILE, Praat, Parselmouth, ppgs and Whisper; populate conforms_to_schema and a was_derived_from link to the raw audio source.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/VOICE_2026-08-28agentic_rep1_evaluation.json` `/assessment/recommendations/4`

- Without sources, request (unsure): requests; versions/URLs for tools may be criticism of held entries, rating not visible
- With sources, criticism: Names held tools and asks for versions/URLs; rating faults their missing versions and URLs.

#### q19r-050: request (without) / criticism (with); first criticism, now agrees with the first

> Mirror the version lineage into was_derived_from and parent_datasets, and attribute the disclosed 419,614-byte residual so both provenance and size arithmetic are machine-checkable in the slots consumers query.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v7_rep3_r20_rating1_evaluation.json` `/assessment/recommendations/7`

- Without sources, request (unsure): mirror lineage (no location); 'attribute the residual' may be criticism, rating not visible
- With sources, criticism (unsure): Asks to attribute the disclosed byte residual; rating faults it as unattributed (mirror part has no location).

#### q19r-065: request (without) / criticism (with); first criticism, now agrees with the first

> Populate parent_datasets with doi:10.60775/fairhub.2 and set was_derived_from to the same identifier, keeping the study-name prose in notes.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-09-04gapi_rep2_evaluation.json` `/semantic_analysis/issues_detected/2/recommendation`

- Without sources, request (unsure): request; notes mention concerns study-name prose, not the slot's content
- With sources, criticism (unsure): Objects to was_derived_from holding study-name prose; rating faults it.

#### q19r-093: request (without) / criticism (with); first criticism, now agrees with the first

> Populate was_derived_from and parent_datasets so the derivation path is machine-readable, and add file_collections with byte totals and file counts alongside an expanded variables list covering the principal phenotype columns.

Source: `data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v7_rep1_r20_rating1_evaluation.json` `/assessment/recommendations/4`

- Without sources, request: plain requests
- With sources, criticism: Asks for an expanded variables list; rating faults variables as only four columns.

#### q19r-114: placement (without) / request (with); first placement, now disagrees with the first

> Record the June 2025 revision and post-publication file additions as errata entries, and consider expressing the FAIRSCAPE provenance lineage as was_derived_from/parent_datasets links in the record itself.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/superseded_fable5/CM4AI_2026-09-01api_rep2_evaluation.json` `/assessment/recommendations/3`

- Without sources, placement (unsure): FAIRSCAPE provenance lineage held outside the record (file)
- With sources, request (unsure): Requests errata and provenance links; FAIRSCAPE not clearly a location in the record.

#### q19r-115: criticism (without) / request (with); first request, now agrees with the first

> Record the publisher as a URI (https://fairhub.io) so Q13 sustainability consumers can find the repository in the structured slot.

Source: `data/evaluation_llm/rubric20_semantic/label_aware/AI_READI_2026-08-28dapi_rep1_evaluation.json` `/semantic_analysis/issues_detected/12/recommendation`

- Without sources, criticism (unsure): asks held publisher to be a URI instead; rating not checked
- With sources, request: publisher absent per rating; no populated value named.

#### q19r-118: request (without) / criticism (with); first criticism, now agrees with the first

> State character encoding (presumably UTF-8) on the text formats and add a was_derived_from statement summarising the raw-to-release derivation.

Source: `data/evaluation_llm/rubric10_semantic/reference_2026-09-11/AI_READI_v7_rep1_r10_rating3_evaluation.json` `/semantic_analysis/issues_detected/8/recommendation`

- Without sources, request: plain request
- With sources, criticism (unsure): Asks for encoding on the held text formats; rating faults its absence.

<!-- END GENERATED -->

## Reading the disagreements

- **Step 3b did what it was missing for.** Without the ratings, 9 of the 11
  disagreements were items the first reading calls criticism and the second
  called request. With the ratings, the reader of record agrees with the first
  reading on 7 of those 9 (`q19r-001`, `-011`, `-013`, `-050`, `-065`, `-093`,
  `-118`). In each, it quotes or paraphrases the rating's fault that the first
  reading's reason quotes. It also agrees on `q19r-115`: the rating says the
  publisher is absent, so no held value is named. Step 3 versus 4 kappa rises
  from 0.539 to 0.917.
- **`q19r-092` and `q19r-121`** stay criticism (first) / request (second). Both
  sentences name the RO-Crate. The reader of record takes the RO-Crate to be
  the object of the request, a release artifact that step 3a says is not a
  value the record holds. The first reading takes the objection to fall on a
  held value: `file_collections`, whose listed archives the rating says carry no
  stated provenance graph (`-092`) and no `was_generated_by` (`-121`). The
  rubric does not say which reading of such a sentence wins when it names both
  a held slot and a release artifact. Not changed here.
- **Steps 1-2 (the misses).** The readings of record differ on one item,
  `q19r-114`. The first reading classes it as a placement: "the FAIRSCAPE
  provenance lineage" says where the lineage is, inside the RO-Crate metadata
  archive, a file. The reader of record calls it a request, unsure, because
  FAIRSCAPE is "not clearly a location in the record". The rubric's step 2 does
  not ask whether the location is in the record; it lists "a file". The reading
  without sources had classed it placement, agreeing with the first. The
  reader of record flagged the same open question in its report: whether a
  release artifact or the RO-Crate counts as a step-2 location. It classed five
  other such items (`027`, `099`, `105`, `109`, `110`) as placement, unsure.
  Filed as a follow-up for adjudication, not changed here.
- **`q19r-006`**, the one step 1-2 disagreement of the reading without
  sources, is resolved. The reader of record classes it as a request, as the
  first reading does: the sentence names no location for the content
  `parent_datasets`/`was_derived_from` are to hold.

Nothing here changes a pin, a class, the module docstring's counts or the
lint. The reading of record would move the Q19 miss count by one, from 64 to
63 among the 122 and from 95 to 94 of the 277, and only if `q19r-114` is a
request, which is the open question above. The reading without sources moved
it the other way, to 65 and 96, on `q19r-006`. #3544 reports the 95 as a
count, not a recall ratio, so no precision or recall figure moves.
