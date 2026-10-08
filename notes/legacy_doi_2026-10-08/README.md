# Legacy DOI construction

This is the bounded repair in
[#4670](https://github.com/bridge2ai/data-sheets-schema/issues/4670).

The packaged and hidden TSV builders now give the `doi` target its own
construction rule. Previously a bare source DOI such as `10.1234/MixedCase`
became `https://doi.org/10.1234/MixedCase`, contradicting the Dataset schema's
bare-DOI requirement. Generic URI targets keep their existing behavior.

Recognized scalar `doi:`, HTTP(S) `doi.org`, and HTTP(S) `dx.doi.org` forms use
the existing `scope.bare_doi` repair parser. Prefix matching is case insensitive;
suffix case is retained. That parser removes surrounding whitespace and trailing
slashes from a prefixed value. Strings already starting with `10.` stay exactly
as supplied, including schema-valid bare forms outside the repair parser's
narrower grammar. The mandatory final Dataset validator still decides whether
a retained value is valid.

Malformed strings, objects, booleans, numbers and lists stay intact in drafts.
A singleton, repeated, mixed or conflicting list never contributes just its
first or recognizable DOI. No source assertion is dropped to obtain a valid
scalar, and returned mutable DOI values do not alias the parser's source data.
Missing/null source properties retain the builder's existing missing-value rule.

When an explicitly selected TSV maps several properties to `doi`, every
nonmissing root assertion is checked. Exact repeated scalar strings agree;
different strings or competing nonscalar values refuse construction. This
includes different spellings of the same DOI: the legacy builder has no
sidecar that retains the discarded alternative, so the caller must explicitly
disambiguate the selected mapping. Member properties cannot fill a missing root
value or participate in its conflict decision. Other targets retain their
existing property precedence.

The current default TSV is unchanged and still omits required `Dataset.id`.
This repair does not make that producer generally schema valid, reroute it,
mint IDs, reinterpret person roles, convert rounded sizes to exact byte counts,
or rewrite historical outputs. Parent issues
[#4594](https://github.com/bridge2ai/data-sheets-schema/issues/4594) and
[#2915](https://github.com/bridge2ai/data-sheets-schema/issues/2915) remain open.
Neither source coverage nor semantic equivalence follows from this correction;
row retirement is not a coverage gain, and intact text does not establish
`exactMatch`/`none`.

## Validation plan

No tests or project replays have run for this draft. Focused controls use both
real builders and the actual closed Dataset validator, plus packaged/hidden
publishers and the API batch path with explicit valid-ID mappings. They cover
accepted forms and case, broad-schema bare values, malformed and non-scalar
preservation, competing source properties, root/member isolation, unchanged
generic URI handling, direct hidden-script imports, and preserved source,
mapping and destination bytes after refusal. A later invalid batch DOI must
prevent every destination replacement.

Run the new `tests/test_rocrate/test_legacy_doi.py` alongside the existing
builder, publication, API result-contract and wrapper regressions after
independent review. Keep all five retained-project legacy replays and their
historical outputs under the parent issue's separate obligations.
