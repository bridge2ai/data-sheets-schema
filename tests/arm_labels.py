"""One definition of which label prefixes are one arm.

Two test modules were carrying byte-identical copies of this table and its
lookup (#1097). Two copies of one fact is one copy nobody updates, and the
shape had a second defect: an allowlist of known suffixes means a *new*
same-day suffix silently forms its own arm. This repository uses those
suffix letters routinely — 2026-08-28 with b, c and d; 2026-09-04 with f and
g — so a v9 arm launched as `2026-09-20a` and `2026-09-20b` would split in
two, and every per-arm uniformity check would pass on the halves.

So arms are declared, not inferred. `ARMS` names each launch date that is one
arm and the prefixes that make it up; `arm_of` raises on a label whose date
is declared but whose suffix is not, which is the case that used to pass.
"""

#: Launch dates that ran as one arm under more than one label prefix, and the
#: exact prefixes that belong to it. A date absent here is its own arm.
ARMS = {
    # #1084: the v8 arm was launched twice on one day — 04f carried CHORUS
    # and VOICE, 04g carried AI_READI and CM4AI. One condition, one arm.
    "2026-09-04": {"suffixes": {"f", "g"}, "name": "2026-09-04v8"},
    # #660/#834: the 2026-08-28 canaries are deliberately separate arms, not
    # one — b, c and d differ in output cap and condition. Declared so that
    # `arm_of` does not raise on them.
    "2026-08-28": {"suffixes": {"", "b", "c", "d"}, "name": None},
}


class UndeclaredArmSuffix(AssertionError):
    """A same-day label suffix nobody has said belongs to an arm."""


def _split(prefix):
    """`2026-09-04f_claude-…` -> ('2026-09-04', 'f', 'claude-…')."""
    head, _, rest = prefix.partition("_")
    date, suffix = head[:10], head[10:]
    return date, suffix, rest


def arm_of(label):
    """The arm a run label belongs to.

    Raises `UndeclaredArmSuffix` when the date is one this file knows to be
    launched under several prefixes and the suffix is not among them: a new
    suffix is a decision about what the arm *is*, and it should be made by a
    person editing `ARMS`, not by a lookup returning a fresh arm.
    """
    prefix = label.rsplit("_rep", 1)[0] if "_rep" in label else label
    date, suffix, rest = _split(prefix)
    declared = ARMS.get(date)
    if declared is None:
        return prefix
    if suffix not in declared["suffixes"]:
        raise UndeclaredArmSuffix(
            f"{label}: {date}{suffix!r} is not one of the declared suffixes "
            f"{sorted(declared['suffixes'])} for {date}. Add it to "
            f"tests/arm_labels.py ARMS if it belongs to that arm, or give it "
            f"its own entry.")
    name = declared["name"]
    return (name + "_" + rest) if name else prefix
