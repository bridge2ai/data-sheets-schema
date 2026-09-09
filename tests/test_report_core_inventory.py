"""#998: the report phase names the core inventory its `both` rule refers to.

The report instruction says `both` is only for a slot the core record
carries, "the core schema declares fewer slots than the full one" — but the
phase was assembled with the `Dataset` digest, so the model's only view of
the core inventory was the completed core record in the carry, where an
empty slot and an undeclared one look the same.
"""

import unittest

from data_sheets_schema import schema_digest
from data_sheets_schema.api_runner import (
    ASSEMBLY_LAYOUT,
    PHASE_INSTRUCTIONS,
    PHASES,
    build_phase,
    core_inventory_block,
)
from tests.test_download.test_api_runner import spec


def _texts(req):
    return [p["text"] for p in req.messages[0]["content"] if p.get("type") == "text"]


class TheReportPhaseCarriesTheCoreInventory(unittest.TestCase):
    def test_every_core_slot_is_named_and_no_full_only_slot_is(self):
        block = core_inventory_block()
        core = set(schema_digest.slot_names("CoreDataset"))
        full = set(schema_digest.slot_names("Dataset"))
        for name in core:
            self.assertIn(f"`{name}`", block)
        for name in sorted(full - core)[:20]:                  # citation, consent_revocations, …
            self.assertNotIn(f"`{name}`", block, name)
        self.assertIn("citation", full - core)                 # the instruction's own example

    def test_it_sits_before_the_instruction_in_the_report_phase_only(self):
        texts = _texts(build_phase(spec(), "report", carry={"Reconciled full record": "x",
                                                             "Completed core record": "y"}))
        self.assertTrue(texts[-2].startswith("# Core schema inventory"))
        self.assertEqual(texts[-1], PHASE_INSTRUCTIONS["report"])   # the instruction stays last (#346)
        for ph in PHASES:
            if ph == "report":
                continue
            self.assertFalse(any(t.startswith("# Core schema inventory") for t in
                                 _texts(build_phase(spec(), ph, carry={}))), ph)

    def test_the_instruction_points_at_the_block_and_the_layout_names_it(self):
        self.assertIn("`# Core schema inventory` block above", PHASE_INSTRUCTIONS["report"])
        self.assertIn("#998", ASSEMBLY_LAYOUT)                 # the assembly digest moves (#353)

    def test_the_block_is_small(self):
        """Names only: the digest is the cached prefix, this is a list."""
        self.assertLess(len(core_inventory_block()), 3000)


if __name__ == "__main__":
    unittest.main()
