"""`build()` hands out a copy, not the cached object (#528).

The cache returned the stored `ClassDigest` by reference, so any caller that
mutated it — or its `nested` entries, or their `ranges`/`enums` dicts — silently
changed what every later `build()` for that class returned, for the life of the
process.

Found when a test stripped `ranges` to check the fingerprint responded, and two
later tests in the same file measured an empty digest and failed. Those failures
read as real defects in the code under test, which is the dangerous shape: the
first instinct is to fix code that was correct.

The exposure is not confined to tests. `build` feeds the generation prompt,
`slot_spec` (what the fitness judge reads) and the fingerprint keying the
fitness and sub-type caches.
"""

import time
import unittest

from data_sheets_schema import schema_digest


class TestMutationIsIsolated(unittest.TestCase):
    def test_clearing_nested_ranges_does_not_persist(self):
        first = schema_digest.build("Dataset")
        self.assertTrue(any(n.ranges for n in first.nested),
                        "no ranges to strip; this test proves nothing")
        for nested in first.nested:
            nested.ranges = {}
        second = schema_digest.build("Dataset")
        self.assertTrue(any(n.ranges for n in second.nested))

    def test_mutating_a_range_dict_in_place_does_not_persist(self):
        """The subtler half: replacing the dict is caught by a shallow copy,
        mutating it is not. Only a deep copy isolates both."""
        first = schema_digest.build("Dataset")
        target = next(n for n in first.nested if n.ranges)
        name = target.name
        target.ranges.clear()
        second = schema_digest.build("Dataset")
        self.assertTrue(next(n for n in second.nested if n.name == name).ranges)

    def test_dropping_slots_does_not_persist(self):
        first = schema_digest.build("Dataset")
        count = len(first.slots)
        first.slots.clear()
        self.assertEqual(len(schema_digest.build("Dataset").slots), count)

    def test_the_rendered_digest_is_unchanged_after_a_mutation(self):
        """The property that actually matters: the generation prompt and the
        cache key must not move because someone inspected a digest."""
        before = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        scratch = schema_digest.build("Dataset")
        scratch.nested.clear()
        scratch.slots.clear()
        after = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        self.assertEqual(before, after)


class TestTheCacheStillWorks(unittest.TestCase):
    """A copy on every call must not turn the memo into a no-op."""

    def test_a_cached_build_is_far_cheaper_than_a_cold_one(self):
        schema_digest.build("Dataset")            # warm
        start = time.perf_counter()
        for _ in range(20):
            schema_digest.build("Dataset")
        cached = (time.perf_counter() - start) / 20

        schema_digest._BUILD_CACHE.clear()
        start = time.perf_counter()
        schema_digest.build("Dataset")
        cold = time.perf_counter() - start

        self.assertLess(cached, cold / 20,
                        f"copy cost {cached*1000:.1f}ms is not cheap against "
                        f"a {cold*1000:.0f}ms cold build")

    def test_equal_content_across_calls(self):
        a = schema_digest.build("Dataset")
        b = schema_digest.build("Dataset")
        self.assertIsNot(a, b)
        self.assertEqual(schema_digest.render(a), schema_digest.render(b))
