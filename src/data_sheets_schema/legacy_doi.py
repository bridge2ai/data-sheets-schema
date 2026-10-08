"""DOI-only construction for the legacy TSV builders; never a validation gate."""
from copy import deepcopy
import re

from data_sheets_schema.scope import bare_doi


_PREFIX = re.compile(r'^(?:doi:|https?://(?:dx\.)?doi\.org/)', re.IGNORECASE)


def doi_value(value):
    """Repair recognised scalar prefixes without discarding source assertions.

    Bare strings stay exactly as supplied, including schema-valid forms outside
    the repair parser's narrower grammar. Malformed strings, objects and lists
    also stay intact for the mandatory Dataset publication validator. In
    particular, a list never contributes only its first or recognisable DOI.
    """
    if isinstance(value, str) and not value.startswith('10.'):
        source = value.strip()
        prefix = _PREFIX.match(source)
        if prefix is not None and bare_doi(source) is not None:
            # The recognizer strips trailing '/' for its comparison policy.
            # It admits the repair, but only the representation prefix may be
            # removed here: every suffix character remains source evidence.
            return source[prefix.end():]
    return deepcopy(value)


def source_value(parser, properties):
    """Read all declared DOI sources, refusing unequal competing assertions.

    Exact repeated scalar strings need no precedence decision. Even equivalent
    DOI spellings in different source properties are otherwise left for the
    caller to disambiguate, rather than silently dropping one assertion.
    Other targets retain the legacy builder's ordinary first-property policy.
    """
    present = [(name, parser.get_property(name)) for name in dict.fromkeys(properties)]
    present = [(name, value) for name, value in present if value is not None]
    if not present:
        return None
    first = present[0][1]
    if len(present) > 1 and not (
        isinstance(first, str)
        and all(isinstance(value, str) and value == first for _, value in present)
    ):
        names = ', '.join(name for name, _ in present)
        raise ValueError(f"Conflicting DOI source assertions ({names}); no value was selected")
    return first
