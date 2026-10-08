# Legacy DOI construction

This is the bounded repair in
[#4670](https://github.com/bridge2ai/data-sheets-schema/issues/4670).

The packaged and hidden TSV builders now give the `doi` target its own
construction rule. Previously a bare source DOI such as `10.1234/MixedCase`
became `https://doi.org/10.1234/MixedCase`, contradicting the Dataset schema's
bare-DOI requirement. Generic URI targets keep their existing behavior.

Recognized scalar `doi:`, HTTP(S) `doi.org`, and HTTP(S) `dx.doi.org` forms use
the existing `scope.bare_doi` parser only to recognize an eligible repair.
Prefix matching is case insensitive; the entire suffix, including its case and
one or more trailing slashes, is taken from the source string. After the existing
outer-whitespace trim, only the known representation prefix is removed. The
parser's slash-stripped return value is never used as the constructed DOI.
Strings already starting with `10.` stay exactly as supplied, including
schema-valid bare forms outside the repair parser's narrower grammar. The
mandatory final Dataset validator still decides whether a retained value is valid.

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

## Suffix-preservation correction

The second review round found [#4671](https://github.com/bridge2ai/data-sheets-schema/issues/4671)
before publication: the first implementation used the recognizer's return value,
which removed trailing slashes from prefixed DOI suffixes. The earlier suite
covered this ending only for bare inputs. The correction removes only the known
prefix and preserves the complete suffix. Root and independent source review
found no further issues before the fresh run below.

The [initial 318-test evidence](validation_initial_318.json) is retained as the
exact original file, pinned to `f85d132ebdb3b26c1d80d6414ec39220c226334d`, tree
`5371e1734c2f7aeed14b1c0668c3154dbc3136e2`. It does not validate the suffix fix.
Its external artifact `legacy-doi-tests-01.xml` remains 51,571 bytes, SHA-256
`30c50542813c258f877d4631d55341ab69cbe564b0afb2de163465a4d6ce3905`.
That run recorded 43.473 seconds in XML and 43.51 seconds plus 14 dependency
warnings in the coordinator's terminal.

## Current validation results

The fresh serialized eight-module run passed **356 tests**, with zero failures,
errors or skips, at commit
`1a98255bb28451500d4864876a16d9c6c2f6b435`, tree
`1935f1c16c676cadb695403a05803b39f1aa1b95`. The coordinator's terminal reported
44.83 seconds and 14 dependency deprecation warnings. JUnit records 44.795
seconds; XML does not encode the warning count or attest the tested commit.

| Module | Passed |
| --- | ---: |
| `tests/test_rocrate/test_legacy_doi.py` | 155 |
| `tests/test_fairscape_integration/test_d4d_builder.py` | 37 |
| `tests/test_rocrate/test_legacy_publication.py` | 51 |
| `tests/test_rocrate/test_legacy_publication_adversarial.py` | 39 |
| `tests/test_rocrate/test_legacy_result_contract.py` | 19 |
| `tests/test_rocrate/test_legacy_envelope_adversarial.py` | 28 |
| `tests/test_cli/test_rocrate_transform_mapping.py` | 17 |
| `tests/test_cli/test_rocrate_transform_mapping_adversarial.py` | 10 |

The DOI module's 155 cases exercise both real builders and the current closed
Dataset validator, packaged/hidden publishers, the API batch path with an
explicit valid-ID mapping, and direct hidden-script use from another working
directory. The additional 38 cases cover all accepted prefix families with
mixed-case suffixes, internal slashes, one/multiple trailing slashes, outer
whitespace and retained malformed/unrecognized forms. The suffix matrix checks
actual published YAML bytes. Existing malformed/list/conflict, root/member and
later-invalid-batch preservation controls also passed.

[validation.json](validation.json) records the current command with symbolic
paths, the eight module counts, 26 selected source/test/resource/dependency pins,
and the original evidence-file hash. Every current selected file was compared
byte-for-byte with the fresh tested Git blob. These pins cover the named files,
not a complete installed environment. The retained external artifact
`legacy-doi-tests-02.xml` is 58,425 bytes, SHA-256
`037a764a6cb1ed8594fa748d682e5f86d3b1c9aabee2bb9da7d25580cceb5934`.
Only evidence notes changed after this fresh run; production and tests are unchanged.

No real-project replay, provider call, scientific rating or new historical label
was produced. All five retained-input legacy replays and the remaining default
construction defects remain obligations of #4594; #2915 stays open. These software
controls establish this DOI slice, not overall legacy mapping repair.
