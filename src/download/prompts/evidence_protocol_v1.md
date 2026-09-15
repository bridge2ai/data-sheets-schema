## Evidence protocol v1

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

For Phase 3, retain the existing audit JSON shape and add an evidence array
to every finding. Each element has exactly one of these shapes:

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
For a list member, identity is relative to that member and ends in id or
name; choose the person's or entity's own identity, not an affiliation.
When that identity is nested, both its id and name must remain unchanged;
the check also binds any identifying fields on the containing role wrapper.
Reordering the list does not remove that relationship. For a non-list field,
omit identity and remove the unsupported field entirely. Do not merely delete
the name or identifier from an otherwise retained unsupported entry.
Every indexed ancestor must also have an original id or name. Preserve all
identifying fields of the remaining members, including their spelling. A
missing, changed, duplicated or newly introduced identity in that container
makes removal ambiguous; stop for review rather than claiming verification.

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
"## Evidence assertions", containing only a JSON code block with this shape:

    {"claims": [
      {"artifact": "original_core", "path": "@header", "op": "lacks", "quote": "# Phase 4 reconciliation: completed"},
      {"artifact": "final_core", "path": "@header", "op": "contains", "quote": "# Phase 4 reconciliation: completed"}
    ]}

These are format examples, not facts to copy into a report. Populate the
array from assertions actually made about this run's artifacts and sources.
If none are made, use an empty claims array and do not imply a nonzero check.
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
