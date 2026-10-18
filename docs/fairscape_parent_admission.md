# Reverse-converter parent admission

The FAIRSCAPE reverse converter writes the selected root's `isPartOf` references
to `parent_datasets` only when the source explicitly identifies an unambiguous
Dataset (#4047). It does not infer an organization, project or Dataset from URI
spelling, fetch external identities, or reroute refused values to another slot.

The six accepted type spellings are `Dataset`, `schema:Dataset`,
`http://schema.org/Dataset`, `https://schema.org/Dataset`, `evi:Dataset`, and
`https://w3id.org/EVI#Dataset`. A type may be a string or a nonempty list of strings.
The accompanying types `ROCrate`, `evi:ROCrate`, `https://w3id.org/EVI#ROCrate`,
`prov:Entity`, and `http://www.w3.org/ns/prov#Entity` are allowed only alongside a
Dataset type. Every supplied inline or graph type must satisfy this finite
policy; an absent type can be supplied by the other source. Unknown co-types are
unsupported policy evidence, not proof of ontology disjointness or source error.

Only an immediate object with a nonempty textual `@id` is a reference. Strings
remain literals. Parent IDs with surrounding whitespace are refused without
changing global identifier handling. Graph lookup uses the exact raw ID and
counts all matching nodes before examining types. Duplicate graph identities
are refused, including identical duplicates. Inline Dataset typing can suffice
without a graph match; an untyped reference needs one uniquely typed match.
Graph names, descriptions and other metadata are not copied into the output.

The existing iterative ancestry check refuses known root links, cycles,
duplicate ancestor identities, and paths exceeding 10,000 visits. Both inline
and graph edges count. Shared acyclic ancestors are supported; an unresolved
external ancestor is an unresolved leaf, not evidence of global acyclicity.
An inline `id` must equal its examined `@id` or that ID's existing ARK resolver
form. Ordinary fitting and identifier precedence are then preserved.

After fitting a parent, its actual output ID must differ from the root ID the
converter already produced (#4946). This catches equality introduced by a
preferred root `identifier` or existing DOI/ARK shaping. It does not introduce
new identifier-equivalence rules or run the root-ID calculation or fitter twice.
Reference order, repeated occurrences and original diagnostic indexes remain.
Later ordinary schema validation may still reject an admitted parent's fields.

`converter.parent_evidence` returns detached parsed-JSON admission decisions.
Each records the root identity/index, exact source pointer, original occurrence,
raw reference, every matching graph member, supplied types, consulted ancestry,
reason and available output identity. A scalar `isPartOf` uses its property
pointer and logical occurrence zero. Missing, null and an empty list have no
occurrences. An admission decision is not a promise of final schema retention.

Each policy refusal also appears in the existing `dropped` channel at
`isPartOf[original_index]`. After `; parent_evidence=` the message contains the
complete JSON decision with ASCII escaping. The existing save method, module
CLI and `fairscape-cli rocrate-to-d4d` expose it without requiring a new sidecar
or flag. Escaping preserves non-BMP characters, lone surrogates, control text,
lists, ordering and false-versus-zero values. It does not preserve original JSON
whitespace or claim whole-source byte fidelity. Unsupported direct-Python values
in consulted parent evidence (cycles, exotic objects, non-text keys or nonfinite
numbers) raise before the converter writes a Dataset file; unrelated crate
values do not undergo a new serialization pass.

These rules are converter-only. The static mapper, mapping declarations,
coverage denominators, legacy builder policies, retained outputs and figures
are unchanged. Explicit source Dataset typing does not establish the truth of
the relationship, scientific suitability, exact mapping equivalence or losslessness.
