"""Does a record's declared input still hash to what the record consumed? (#452)

The mirror of `d4d download audit-bundles` (#446) one layer up. That command
asks whether a derived bundle still matches what its inputs produce; this asks
whether a *record's* declared input still matches what the record read.

The distinction the whole check rests on: a drifted record is not wrong. It
correctly states the bytes it consumed. What it has lost is the ability to be
re-derived from the path it names, which is a caveat rather than a defect —
hence reported and never fatal, like the unobserved-values counter (#447).
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import (
    BUNDLE_ABSENT,
    BUNDLE_CURRENT,
    BUNDLE_DRIFTED,
    BUNDLE_UNRECORDED,
    bundle_drift,
    bundle_drift_detail,
)


class TestBundleDrift(unittest.TestCase):
    LABEL, METHOD, PROJECT = "2026-08-11_drift_rep1", "claudecode_agent", "VOICE"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.concat = self.root / "data/d4d_concatenated"
        (self.concat / f"{self.METHOD}_core" / self.LABEL).mkdir(parents=True)
        self.bundle = self.root / "bundle.txt"

    def _write(self, *, content=b"the bytes the run consumed", md5=None,
               path=None, omit_hash=False, omit_record=False):
        if content is not None:
            self.bundle.write_bytes(content)
        if omit_record:
            return
        inputs = {"bundle_path": str(path if path is not None else self.bundle)}
        if not omit_hash:
            inputs["bundle_md5"] = md5 or hashlib.md5(content).hexdigest()
        record = (self.concat / f"{self.METHOD}_core" / self.LABEL
                  / f"{self.PROJECT}_provenance.yaml")
        record.write_text(yaml.safe_dump({"inputs": inputs}), encoding="utf-8")

    def _status(self):
        return bundle_drift(self.METHOD, self.LABEL, self.PROJECT, self.concat)

    def test_an_unchanged_bundle_is_current(self):
        self._write()
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_CURRENT)
        self.assertIsNone(reason)

    def test_a_changed_bundle_drifts(self):
        """The case the corpus is in: #421 stripped curator notes from bundles
        55 records already pinned."""
        self._write()
        self.bundle.write_bytes(b"the bytes after a later, correct strip")
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_DRIFTED)
        self.assertIn("now hashes", reason)

    def test_a_change_after_a_first_read_is_still_detected(self):
        """Guards the decision not to memoise the hash (#469).

        The obvious optimisation is to cache the md5 by path — 158 records hash
        12 distinct bundles. A path-keyed cache would answer `current` here on
        the second call, which is precisely the drift the function exists to
        detect. Two calls either side of an edit, so the guard fires if anyone
        adds one.
        """
        self._write(content=b"before")
        self.assertEqual(self._status()[0], BUNDLE_CURRENT)
        self.bundle.write_bytes(b"after!")          # same length, new bytes
        self.assertEqual(self._status()[0], BUNDLE_DRIFTED)

    def test_a_single_byte_is_enough(self):
        """Not a heuristic — the record pins an md5, so any edit drifts it."""
        self._write(content=b"aaaa")
        self.bundle.write_bytes(b"aaab")
        self.assertEqual(self._status()[0], BUNDLE_DRIFTED)

    def test_a_missing_bundle_is_absent_not_drifted(self):
        """Distinct because the remedies differ: a drifted path can still be
        read and diffed, a deleted one cannot."""
        self._write()
        self.bundle.unlink()
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_ABSENT)
        self.assertIn("does not exist", reason)

    def test_no_recorded_hash_is_not_a_pass(self):
        """`unrecorded` must never be counted as `current`.

        86 records carry no bundle hash. Folding them into the matching count
        would report the corpus as far healthier than it is — the same error as
        treating an absent cache entry as a hit.
        """
        self._write(omit_hash=True)
        self.assertEqual(self._status()[0], BUNDLE_UNRECORDED)

    def test_a_missing_provenance_record_is_unrecorded(self):
        self._write(omit_record=True)
        self.assertEqual(self._status()[0], BUNDLE_UNRECORDED)

    def test_the_detail_form_returns_the_declared_path(self):
        """So a caller grouping by bundle need not parse the reason string."""
        self._write()
        status, _reason, declared = bundle_drift_detail(
            self.METHOD, self.LABEL, self.PROJECT, self.concat)
        self.assertEqual(status, BUNDLE_CURRENT)
        self.assertEqual(declared, str(self.bundle))

    def test_the_declared_path_survives_a_missing_hash(self):
        """Grouping still works for records that recorded a path but no hash."""
        self._write(omit_hash=True)
        _status, _reason, declared = bundle_drift_detail(
            self.METHOD, self.LABEL, self.PROJECT, self.concat)
        self.assertEqual(declared, str(self.bundle))

    def test_the_record_is_read_not_the_live_config(self):
        """The comparison is against the path the *record* declares.

        A check that resolved the bundle from the current project config would
        report `current` for a record whose declared path had since been
        repointed — the drift it exists to find.
        """
        other = self.root / "somewhere_else.txt"
        other.write_bytes(b"a different bundle entirely")
        self._write(content=b"original", path=other,
                    md5=hashlib.md5(b"original").hexdigest())
        self.assertEqual(self._status()[0], BUNDLE_DRIFTED)


MANIFEST = Path("data/preprocessed/source_manifest.yaml")


def _history_befores(manifest: Path = MANIFEST) -> set[str]:
    """Every md5 the manifest's `bundle_hash_history` names as a `before`.

    An `after` is not an acknowledgment of anything: a hash that is only an
    `after` is a bundle no later event has replaced, and a record pinning it
    should be `current`. Only a `before` says "this hash was superseded, and
    here is why".
    """
    history = (yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
               ).get("bundle_hash_history") or {}
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "before" and isinstance(value, str):
                    found.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(history.get("events") or [])
    return found


BUNDLE_DIR = Path("data/preprocessed/concatenated")


def _history_terminal(manifest: Path = MANIFEST) -> dict[str, tuple[str, int]]:
    """For every bundle the history names, the `after` of its last event.

    Two shapes, both present in the manifest: `projects.<P>` is
    `<P>_preprocessed.txt`, `crate_bundles.<P>` is
    `<P>_preprocessed_with_crate.txt`. The last `after` is the hash the
    history claims is live — which is what an unrecorded rewrite breaks
    even when no record pins the hash it replaced (#935 review).
    """
    history = (yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
               ).get("bundle_hash_history") or {}
    terminal: dict[str, tuple[str, int]] = {}
    for event in history.get("events") or []:
        for key, suffix in (("projects", "_preprocessed.txt"),
                            ("crate_bundles", "_preprocessed_with_crate.txt")):
            for project, hashes in (event.get(key) or {}).items():
                after = (hashes or {}).get("after")
                if isinstance(after, str):
                    terminal[f"{project}{suffix}"] = (after, event.get("issue"))
    return terminal


def _pinned_md5(method: str, label: str, project: str) -> str:
    from data_sheets_schema.provenance import record_path_for
    record = yaml.safe_load(record_path_for(project, method, label)
                            .read_text(encoding="utf-8")) or {}
    return str((record.get("inputs") or {}).get("bundle_md5"))


class TestWhatTheHistoryExplains(unittest.TestCase):
    """The invariant's edge: only a `before` acknowledges a drift."""

    def _manifest(self, events):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "source_manifest.yaml"
        path.write_text(yaml.safe_dump({"bundle_hash_history":
                                        {"events": events}}), encoding="utf-8")
        return path

    def test_a_before_explains_a_drift_and_an_after_does_not(self):
        path = self._manifest([{"issue": 1, "projects": {
            "P": {"before": "aaaa", "after": "bbbb"}}}])
        explained = _history_befores(path)
        self.assertIn("aaaa", explained)
        # A record pinning `bbbb` should be current; if it has drifted, the
        # rewrite that replaced `bbbb` is the unrecorded event.
        self.assertNotIn("bbbb", explained)

    def test_the_terminal_hash_is_the_last_events_after_per_bundle(self):
        path = self._manifest([
            {"issue": 1, "projects": {"P": {"before": "a1", "after": "a2"}},
             "crate_bundles": {"P": {"before": "c1", "after": "c2"}}},
            {"issue": 2, "projects": {"P": {"before": "a2", "after": "a3"}}},
        ])
        self.assertEqual(_history_terminal(path), {
            "P_preprocessed.txt": ("a3", 2),
            "P_preprocessed_with_crate.txt": ("c2", 1)})

    def test_no_history_explains_nothing(self):
        self.assertEqual(_history_befores(self._manifest([])), set())
        empty = self._manifest([])
        empty.write_text("{}", encoding="utf-8")
        self.assertEqual(_history_befores(empty), set())


@unittest.skipUnless(Path("data/d4d_concatenated").exists(), "corpus absent")
class TestAgainstTheRealCorpus(unittest.TestCase):
    def test_every_drift_is_a_named_event(self):
        """A corpus-wide input change must be acknowledged, not absorbed —
        which is the whole defect: #421 and #445 both changed bundles
        correctly and neither was detected.

        Until #910 this pinned the drift count (64 when #452 was filed, 68
        after #539), so the next bundle change would fail here and be
        acknowledged by updating the number. It was: the mojibake repair
        (#874) moved it to 109 and the docx/accent fixes (#921) to 136, and
        each time the acknowledgment already existed in a better place — the
        manifest's `bundle_hash_history`, which names the md5 every event
        replaced. So the invariant is the history itself: a drifted record
        pins a hash that some recorded event names as its `before`. A
        rewrite nobody recorded leaves records pinning a hash no event
        explains, and that is what fails now; the count is reported, never
        asserted.
        """
        from data_sheets_schema.runs import discover, is_complete

        explained = _history_befores()
        self.assertGreater(len(explained), 0, "no bundle_hash_history events")
        counts = {BUNDLE_CURRENT: 0, BUNDLE_DRIFTED: 0,
                  BUNDLE_ABSENT: 0, BUNDLE_UNRECORDED: 0}
        unexplained = []
        for run in discover():
            # The same filter `d4d runs check` applies. `discover` yields the
            # full and _core methods as separate runs over one provenance
            # record, so counting both doubles every figure.
            if run.is_core or run.deterministic:
                continue
            for project in run.projects:
                if not is_complete(run.method, run.label, project):
                    continue
                status, _reason, declared = bundle_drift_detail(
                    run.method, run.label, project)
                counts[status] += 1
                if status in (BUNDLE_DRIFTED, BUNDLE_ABSENT):
                    pinned = _pinned_md5(run.method, run.label, project)
                    if pinned not in explained:
                        unexplained.append(
                            f"{run.label} {project}: pins {pinned[:8]} for "
                            f"{Path(declared).name}, named by no event")
        self.assertEqual(unexplained, [],
                         "drifted records whose pinned bundle hash no "
                         "bundle_hash_history event names as `before` "
                         f"(counts: {counts})")
        # No floor on `current` any more (it was 12, then 41 by 2026-09-03):
        # a drop is what a *recorded* rewrite legitimately does to the records
        # that were current, and an unrecorded one is what the test below
        # catches. The counts are in the message above, not asserted.

    def test_every_bundle_the_history_names_still_hashes_to_its_last_after(self):
        """The half the invariant above cannot see (#935 review).

        A drift is only visible through a record that pins the replaced
        hash, and the #427 event recorded CHORUS with before == after (the
        strip removed nothing there), so CHORUS's live hash is already a
        `before` and an unrecorded rewrite of it would have passed. The
        history's own claim closes that: the last event's `after` for each
        bundle it names is the hash that should be live, whatever the
        records pin. Recording the rewrite is the way to make this pass.
        """
        terminal = _history_terminal()
        self.assertGreater(len(terminal), 0)
        stale = []
        for name, (after, issue) in sorted(terminal.items()):
            bundle = BUNDLE_DIR / name
            if not bundle.exists():
                stale.append(f"{name}: missing; history (#{issue}) says {after[:8]}")
                continue
            live = hashlib.md5(bundle.read_bytes()).hexdigest()
            if live != after:
                stale.append(f"{name}: hashes {live[:8]}, history's last event "
                             f"(#{issue}) says {after[:8]}")
        self.assertEqual(stale, [], "bundles rewritten with no bundle_hash_history "
                                    "event recording it")
