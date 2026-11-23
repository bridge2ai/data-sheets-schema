# Purpose: one-off edit of tests/test_q19_rationale_lint.py. Moves the five
#   recommendation pins added for the 2026-11-22 general_context_v3 evaluations
#   out of `_RECOMMENDATIONS_READ` (the 122 pins the #3831 blind second reading
#   covers; tests/test_q19_blind_second_reading.py requires that dict to be
#   exactly the packet) into `_RECOMMENDATIONS_READ_2026_11_22`, and makes the
#   recall test read both.
# Inputs: tests/test_q19_rationale_lint.py (working tree). Outputs: the same file.
# Serves: PR 6309 (data/agentic-v9-opus55-final-20261122). Date: 2026-11-22.
from pathlib import Path

p = Path("tests/test_q19_rationale_lint.py")
t = p.read_text(encoding="utf-8")

old_block = '''        # Added 2026-11-22: the five recommendations the general_context_v3
        # evaluations of the 2026-11-22b records add, read by the same
        # ordered test against their own ratings. None names an absence as a
        # noun or state (step 1); none says where the content of a slot it
        # asks for is now (step 2: "structured" and "dedicated" name the
        # target form, not another holder); none names a populated value it
        # objects to (step 3: every slot it names is listed absent in its
        # rating). Requests, like "Express the conversion and QC chain as
        # PROV-O" above.
        "Add structured derivation links (raw audio and REDCap sources",
        "Add top-level resources/parent_datasets links and a confidentiality_level",
        "Populate regulatory_restrictions.confidentiality_level and link",
        "Populate the dedicated fields where source information exists",
        "Record a confidentiality classification, IP restrictions",
    ],
}
'''
new_block = '''    ],
}

# Added 2026-11-22: the five recommendations the general_context_v3
# evaluations of the 2026-11-22b records add, read by the same ordered test
# against their own ratings. None names an absence as a noun or state (step
# 1); none says where the content of a slot it asks for is now (step 2:
# "structured" and "dedicated" name the target form, not another holder);
# none names a populated value it objects to (step 3: every slot it names is
# listed absent in its rating). Requests, like "Express the conversion and QC
# chain as PROV-O" above.
#
# Kept apart from `_RECOMMENDATIONS_READ` on purpose: that dictionary is the
# first reading of the 122 sentences in the #3831 packet, which two blind
# second readings cover (tests/test_q19_blind_second_reading.py requires it
# to be exactly the packet). These five have this one reading and no second.
_RECOMMENDATIONS_READ_2026_11_22 = {
    "request": [
        "Add structured derivation links (raw audio and REDCap sources",
        "Add top-level resources/parent_datasets links and a confidentiality_level",
        "Populate regulatory_restrictions.confidentiality_level and link",
        "Populate the dedicated fields where source information exists",
        "Record a confidentiality classification, IP restrictions",
    ],
}
'''
assert t.count(old_block) == 1
t = t.replace(old_block, new_block)

old_loop = '''    sorted_ = {}
    for kind, fragments in _RECOMMENDATIONS_READ.items():
        for fragment in fragments:
            hits = _pinned(fragment, recommendations)
            assert len(hits) == 1, (kind, fragment)
            assert hits[0] not in sorted_, (kind, fragment)
            sorted_[hits[0]] = kind
    assert set(sorted_) == set(recommendations)
'''
new_loop = '''    sorted_ = {}
    for pins in (_RECOMMENDATIONS_READ, _RECOMMENDATIONS_READ_2026_11_22):
        for kind, fragments in pins.items():
            for fragment in fragments:
                hits = _pinned(fragment, recommendations)
                assert len(hits) == 1, (kind, fragment)
                assert hits[0] not in sorted_, (kind, fragment)
                sorted_[hits[0]] = kind
    assert set(sorted_) == set(recommendations)
'''
assert t.count(old_loop) == 1
t = t.replace(old_loop, new_loop)

old_c = '''    # five of 2026-11-22) are read by hand like the 155, and every one is
    # pinned by one fragment to one class (#3747).
'''
new_c = '''    # five of 2026-11-22) are read by hand like the 155, and every one is
    # pinned by one fragment to one class (#3747). The five are pinned in
    # `_RECOMMENDATIONS_READ_2026_11_22`; no blind second reading covers them.
'''
assert t.count(old_c) == 1
t = t.replace(old_c, new_c)

old_d = '''    a recommendation verb, read by hand as requests (127 recommendations,
    45 requests). The 155 read sentences and their classes are unchanged.
'''
new_d = '''    a recommendation verb, read by hand as requests (127 recommendations,
    45 requests) and pinned in `_RECOMMENDATIONS_READ_2026_11_22`, apart from
    the 122 the #3831 blind second reading covers. The 155 read sentences and
    their classes are unchanged.
'''
assert t.count(old_d) == 1
t = t.replace(old_d, new_d)
p.write_text(t, encoding="utf-8")
print("edited")
