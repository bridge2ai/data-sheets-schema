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

## Validation results

The serialized eight-module run passed **318 tests**, with zero failures,
errors or skips, at commit
`f85d132ebdb3b26c1d80d6414ec39220c226334d`, tree
`5371e1734c2f7aeed14b1c0668c3154dbc3136e2`. The coordinator's terminal reported
43.51 seconds and 14 dependency deprecation warnings. JUnit records 43.473
seconds; its XML does not encode the warning count or attest the tested commit.

| Module | Passed |
| --- | ---: |
| `tests/test_rocrate/test_legacy_doi.py` | 117 |
| `tests/test_fairscape_integration/test_d4d_builder.py` | 37 |
| `tests/test_rocrate/test_legacy_publication.py` | 51 |
| `tests/test_rocrate/test_legacy_publication_adversarial.py` | 39 |
| `tests/test_rocrate/test_legacy_result_contract.py` | 19 |
| `tests/test_rocrate/test_legacy_envelope_adversarial.py` | 28 |
| `tests/test_cli/test_rocrate_transform_mapping.py` | 17 |
| `tests/test_cli/test_rocrate_transform_mapping_adversarial.py` | 10 |

The 117 new cases exercise both real builders and the current closed Dataset
validator, packaged/hidden publishers, the real API batch path with an explicit
valid-ID mapping, and direct hidden-script use from another working directory.
They cover the accepted forms and preservation/refusal boundaries above,
including a later invalid batch DOI preventing every destination replacement.
Existing publication, result-contract and wrapper controls also passed.
Independent adversarial source review found no material issues before execution.

[validation.json](validation.json) records the command with symbolic paths,
the eight module counts, and 26 selected production/test/resource/dependency
pins. Each selected working file was compared byte-for-byte with the tested Git
blob. These pins cover the named files, not a complete installed environment.
The retained external JUnit artifact `legacy-doi-tests-01.xml` is 51,571 bytes,
SHA-256 `30c50542813c258f877d4631d55341ab69cbe564b0afb2de163465a4d6ce3905`.
Only these evidence notes changed after the run; source and tests are unchanged.

No real-project replay, provider call, scientific rating or new historical label
was produced. All five retained-input legacy replays and the remaining default
construction defects remain obligations of #4594; #2915 stays open. The successful
software controls establish this DOI slice, not overall legacy mapping repair.
