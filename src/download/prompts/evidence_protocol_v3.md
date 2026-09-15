## Evidence protocol v3

Apply these rules to every phase. They supplement the schema and evidence
boundary; a valid schema, matching snippet or audit recommendation does not
establish semantic support.

### Relationships and document attribution

Read a structured value as a subject, relationship and object together.
Membership in a leadership team does not establish that a person created
the dataset. A project contact is not necessarily its maintainer or access
committee contact. An affiliation does not turn a person into an institution.
Keep separately established roles, including a stated principal investigator
where the schema permits one. Preserve other supported information in neutral
text, without retaining an unsupported role container.

When an audit identifies an unsupported relationship, its repair must remove
that relationship. "Keep the entry and explain that its role is unstated" is
not a valid repair. Check the audit recommendation against the schema meaning
before applying it. Do not call a retained unsupported relationship addressed.

Check each attributed clause against the document it names, including each
assertion that a second document corroborates a first. A fact appearing
elsewhere in a bundle does not validate an attribution. Name only supporting
documents; do not invent corroboration. For example, a protocol can state a
planned holdout while a repository overview says nothing about it. That fact
may be attributed to the protocol, but not to the overview. A receipt anchored
to the protocol does not repair prose attributing the fact to the overview.

### Audit evidence

For Phase 3, return an audit object with findings, summary and source_review.
Every finding needs an evidence array. Each element has exactly one of these shapes:

    {"source": "protocol.txt", "chunk": "c002", "quote": "an exact source passage"}
    {"artifact": "original_full", "path": "/some_field/details", "op": "contains", "quote": "an exact original passage"}
    {"artifact": "original_full", "path": "/some_field/details", "op": "lacks", "quote": "planned"}

Use the source filename and chunk ID from the selected chunk manifest. Quotes
must occur in that document's named chunk; preserve case and punctuation.
Whitespace and YAML line wrapping are folded. Do not use ellipses to splice
passages. Quote enough governing context to establish the subject and status.

Artifact paths are JSON Pointers, with zero-based list indexes. Use @header
only for the leading YAML comment block. For a number, boolean or null, quote
its complete JSON scalar spelling (for example 12, true or null); scalar
values are matched as a whole. For an allegation that a qualifier
was lost, include a separate lacks assertion at each original location where
you claim it is missing. If it is present, withdraw that allegation. A valid
objection to a method's placement does not validate an adjacent allegation
that the same value lost its "in process" qualifier. Check each subclaim.
An absent path is not evidence that an existing value lost a qualifier.
Quote a containing field or a source passage for an omission finding.

For each rejected relationship also add remove_relationship to its finding:

    {"path": "/creators/1", "identity": "/name"}
    {"path": "/data_governance/committee_contact"}

The path names the unsupported relationship in the original full record.
For a list member, identity is relative to that member and ends in a name or
schema identifier field: id, name, orcid, doi, grant_number, variable_name,
hash, md5, sha256, checksum or target_dataset. Choose the person's or entity's own identity,
not an affiliation.
All present identifiers must remain unchanged, including a person's ORCID;
the check also binds identifying fields on the containing role wrapper.
All nested identifiers in the selected member are bound too; an unchanged
wrapper cannot hide a changed person or resource beneath it. Reordering a
nested collection of identities can make matching ambiguous and needs review.
The remaining members must also retain their structured values, including
scalar relationship targets, so an unchanged wrapper cannot hide a changed
endpoint. Their narrative description, notes and source_caveats may be revised.
If other structured edits to those members are needed, removal is ambiguous
and requires review; do not claim the checker established it.
An identity pointer must follow nested objects, not indexed lists. All
containing objects retain both the presence and absence of these identifier
and name fields; moving a rejected person's identity onto a surviving wrapper fails.
Reordering the list does not remove that relationship. For a non-list field,
omit identity and remove the unsupported field entirely. Do not merely delete
the name or identifier from an otherwise retained unsupported entry.
An indexed ancestor with an original identifier or name must preserve all
identifying fields, including their spelling. A missing, changed, duplicated
or newly introduced identity in that container makes removal ambiguous.

For an anonymous indexed ancestor with no identifier or name, child-field
removals may instead be established from its unchanged structured content.
For example, a removal path can be /instances/0/data_substrate without an
identity property. Do not invent an identifier or treat the old index as one.
All original members must survive, with a unique one-to-one match after
excluding only explicitly declared child-removal paths and narrative
text (description, notes and source_caveats). At least one nonempty structural
value must remain to anchor every member. Matching permits list reordering;
it does not permit new members, member deletion/replacement, renamed types,
changed counts, changed endpoints or other undeclared structured edits.
Declare every supported child removal separately. Only dictionary paths
below anonymous ancestors are supported; another indexed list beneath one
requires review. Anonymous whole-member removal, empty or duplicate remaining
signatures, and removal of narrative fields cannot establish this proof.
Retaining a field with null, a new value or a disclaimer is not its removal.

The v2/v3 checker validates removal preconditions during audit admission, before
reconciliation, including an in-memory projection of all declared removals
at their original positions. If those actions erase the unique structural
correspondence, admission stops without a reconciliation request. That
hypothetical projection never changes the originals or becomes a generated
record. Any ambiguity stops for review. The check establishes only
these declared structural changes, not the semantic correctness of the audit.

### Reconciliation and report

Recheck the original evidence before accepting a proposed repair. Preserve
the original full and derived core before any reconciliation edits. The
original core's header must be read from that original artifact; a header
present only after reconciliation was not present in Phase 2.

Use original_full, original_core, final_full and final_core as artifact names
for report assertions. Every report claim about an original quotation,
qualifier or header needs its own assertion. Each source-attributed factual
clause needs a source assertion. Evidence assertions support the prose; they
do not replace the required Dispositions table.

Before the final Dispositions section, write exactly one section headed
"## Evidence assertions", containing only a JSON code block with exactly two
keys: claims (an array of the source/artifact assertions above), and source_review
(the complete final-record review specified below). An original-core header
claim must use original_core and @header, while a final-core claim must use
final_core and @header. Populate claims from assertions actually made about
this run's artifacts and sources. If none are made, use an empty claims array
and do not imply a nonzero check. source_review remains mandatory in that case.
Report re-checks must preserve and correct this appendix as well as the
Dispositions table. A failed evidence check stops completion.

The checker verifies declared quotations and removal actions. It cannot
establish that every claim was declared, that a quote entails a role, or that
the audit is semantically correct. Independent review of unchanged originals
against all relevant source context remains the acceptance gate.

For native execution, the independent reviewer must also match the snapshot
hashes printed by the actual freeze command's tool result to the preserved
files, and verify from the transcript that the freeze preceded reconciliation.
A model's prose claim that it preserved originals is not this evidence.


### Required source review (v3)

During generation, keep clauses with different document identities or statuses
separate. Do not merge one source's factual clause into another source's
attribution. Describe instructions as instructions, capabilities as capabilities,
and plans as plans. Requests for progress reports do not attest adherence to a
procedure. Inventory descriptions of software to be deployed remain prospective
in every occurrence. A source can change scope locally: read the complete
passage, including governing headings and explicit local changes.

Audit the entire original full record, including claims you intend to retain.
The final report reviews the entire final full record anew. The supplied
source-review inventory enumerates every populated scalar as a JSON Pointer,
its text and whether record metadata is allowed. It includes zero and false;
null, empty strings and empty containers make no populated claim. For native
execution, use the specified read-only inventory commands. Never invent a hash.

Add `source_review` to the audit object. In the report's existing Evidence
assertions JSON block, include both `claims` and `source_review`. The latter has
exactly these keys:

    {"artifact": "original_full or final_full", "sha256": "copy the inventory hash",
     "values": [{"path": "/description", "claims": [
       {"text": "the complete literal clause at this path",
        "verdict": "supported", "attributed_to": [],
        "claim_status": "fact", "source_status": "fact",
        "evidence": [{"source": "protocol.txt", "chunk": "c001",
                      "quote": "a literal source passage with its governing context"}],
        "reason": "why this passage supports this subject, scope and attribution"}
     ]}]}

Use one values entry for every inventory path, exactly once. Split each value
into atomic factual clauses and review each occurrence, even if a similar claim
was reviewed elsewhere. Claim `text` quotations together must cover the entire
value, including punctuation; whitespace wrapping is folded, case and punctuation
are not. Do not hide an unreviewed clause inside a supported composite claim.
For a scalar number or boolean, copy its whole inventory text. Separate members
of a prose inventory when their evidence, document identity or status differs.

`attributed_to` lists the exact source filenames the clause explicitly credits,
including claimed corroboration by a second document. Use an empty list only
when the clause names no source. Match names or titles in the record to the
bundle's documents; do not choose the document that merely contains convenient
text. Every named document must have its own supporting source evidence. A fact
stated only in protocol.txt cannot be attributed to overview.txt. A matching
quote in protocol.txt does not validate prose crediting overview.txt.

`claim_status` and `source_status` each use one of:

- `fact`: a non-operational fact without a governing prospective or progress
  qualifier, such as an established name or an observed count;
- `planned`: a future commitment, intention or proposal;
- `in_progress`: an operation explicitly underway, without established completion;
- `applied`: an operation, adherence, deployment or availability established for
  the particular dataset, subject, release and time in the claim;
- `instruction`: a procedure, requirement or request to perform/report an action;
- `capability`: what a tool or repository can do, without evidence of use on the dataset.

Use `unstated` for source_status when the source does not establish the claimed
state. It cannot support a retained claim. Read the governing clause and local
scope before classifying; a bare matching fragment is insufficient. Do not use
`fact` to conceal an operational or prospective claim. For example, a supported
claim saying that a source describes a planned deployment is `planned`, not
`fact`. Instructions or a progress-report request do not establish that sites
followed them. A capability does not establish its application. A plan does not
prove that deployment did or did not occur. Status must agree for a `supported`
claim; evidence supporting different statuses requires separate claims.
Quantities and presence/completion booleans inherit their governing scope too;
a target quantity under an anticipated-final heading is not an observed count.

Use `verdict: revise` for an unsupported attribution, unsupported status or any
other unsupported clause. Explain the defect in reason. Its evidence may be
empty when no passage supports the assertion, but any quoted passage must still
verify in the named document/chunk. Every original value containing a revise
judgment must be linked to an actionable audit finding by adding `review_paths`
(a list of those JSON Pointers) to the finding. Retain the existing finding
fields and evidence requirements. Final source review must honestly mark any
remaining unsupported claim revise; that stops completion. Do not change the
reviewed record, original audit or source classification to manufacture a pass.

Only an inventory value marked record_metadata_allowed may instead use
`{"path": "...", "metadata_reason": "why this is record structure"}`. This
covers the record's schema/class declarations and nested identifiers minted on
its own id. Dataset identifiers, roles and substantive facts still need source
claims. A metadata exception is not a source-supported factual judgment.

This gate checks exact-artifact coverage, quotations and consistency of declared
attribution/status. It does not independently classify prose, prove entailment,
verify that every clause was correctly split or establish that a model's status
labels are correct. Independent review of the unchanged record and full source
context remains required. A passing gate is not scientific acceptance.

A failed source review is terminal for this attempt, including a missing or
uncheckable review. Do not rewrite a rejected review's classifications to make
it pass, resume the attempt or send another paid request. An ordinary report
claim or Dispositions correction is allowed under the existing single re-check
only while source reviews pass; that re-check must carry a fresh final inventory.
For native execution, independent acceptance must verify the actual check tool
results and confirm the agent stopped on any failed check, as well as verifying
the original-freeze hashes and final artifacts. Current-file validation alone
cannot establish that tool-history requirement.
