"""A resumed phase must not run short of its declared inputs (#575).

`PHASE_NEEDS` states what each phase requires. The resume path built each
request from whichever of those happened to be on hand:

    needed = {k: carry[k] for k in PHASE_NEEDS[ph] if k in carry}

so a phase whose prerequisite was missing ran anyway, with less context than its
instruction assumes, and wrote a record indistinguishable from one produced with
everything. #566 made that concrete: `reconcile_full` now depends on the core
record, and a resume that lost core would absorb nothing while looking normal.

Interrupted runs are not hypothetical — #513 documents a sweep that had to be
stopped, and the resume path exists because an arm takes hours.
"""

import unittest

from data_sheets_schema.api_runner import PHASE_ARTIFACT, PHASE_NEEDS, PHASES


class DeclaredInputsTest(unittest.TestCase):

    def test_every_phase_input_is_produced_by_an_earlier_phase(self):
        """Otherwise a required input could never be satisfiable on resume."""
        produced = {"Completed full record": "full",
                    "Completed core record": "core",
                    "Audit findings": "audit",
                    "Reconciled full record": "reconcile_full"}
        for i, ph in enumerate(PHASES):
            for need in PHASE_NEEDS[ph]:
                with self.subTest(phase=ph, need=need):
                    src = produced.get(need)
                    self.assertIsNotNone(src, f"nothing produces {need!r}")
                    self.assertLess(PHASES.index(src), i,
                                    f"{ph} needs {need}, produced later")

    def test_reconcile_full_declares_the_core_record(self):
        """The dependency #566 added, and the one #575 can strand."""
        self.assertIn("Completed core record", PHASE_NEEDS["reconcile_full"])


class ResumeGuardTest(unittest.TestCase):
    """Read from the source of `execute`, which is where the logic lives.

    Exercising it for real would need a live client and six phases of spend;
    these assert the two properties that were wrong, both of which are visible
    in the control flow.
    """

    def _source(self):
        import inspect

        from data_sheets_schema.api_runner import execute
        return inspect.getsource(execute)

    def test_a_missing_declared_input_stops_the_phase(self):
        src = self._source()
        self.assertIn("declares inputs", src)
        self.assertNotIn("for k in PHASE_NEEDS[ph] if k in carry", src,
                         "the filtering form is what allowed a short run")

    def test_discarding_an_artifact_discards_its_whole_dependency_closure(self):
        """One level was not enough (#601).

        `reconcile_core` and `report` need the *reconciled* full record, not the
        completed one, so neither named a discarded `Completed full record` and
        neither was invalidated. After `reconcile_full` re-ran with different
        bytes they could stay in `done` and be skipped — shipping a core record
        and a report reconciled against a full record that no longer exists.
        """
        from data_sheets_schema.api_runner import PHASES, _dependents_of
        closure = _dependents_of("Completed full record",
                                 ("full", "reconcile_full"))
        for phase in ("core", "audit", "reconcile_full", "reconcile_core",
                      "report"):
            with self.subTest(phase=phase):
                self.assertIn(phase, closure)

    def test_a_changed_artifact_invalidates_even_when_still_record_shaped(self):
        """`_looks_like_a_record` cannot tell *which* record it is looking at.

        Progress now stores the md5 of each artifact the completed phases were
        computed against, so bytes that changed between passes invalidate the
        work that depended on them — the same reasoning that pins a validation
        or pair verdict to its artifacts (#426, #544).
        """
        src = self._source()
        self.assertIn("artifact_md5", src)
        self.assertIn("_dependents_of", src)

    def test_the_message_names_the_way_out(self):
        """A gate that stops a paid run must say what to do next."""
        self.assertIn("--no-resume", self._source())


class ArtifactConsumerTest(unittest.TestCase):

    def test_the_core_record_has_consumers_that_would_be_stranded(self):
        """The concrete case: dropping `core` must also drop `audit` and
        `reconcile_full`, or they resume against a record that is gone."""
        consumers = {ph for ph in PHASES
                     if "Completed core record" in PHASE_NEEDS.get(ph, ())}
        self.assertIn("audit", consumers)
        self.assertIn("reconcile_full", consumers)
        self.assertEqual(PHASE_ARTIFACT.get("core"), "core")


if __name__ == "__main__":
    unittest.main()
