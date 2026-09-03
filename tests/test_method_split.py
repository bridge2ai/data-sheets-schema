"""#690 (v8 plan D6): the API runtime's baseline directory."""
import unittest


class TestMethodSplit(unittest.TestCase):
    def test_the_api_baseline_writes_under_claudecode_api(self):
        from data_sheets_schema.cli.api import ARMS
        self.assertEqual(ARMS["baseline"][1], "claudecode_api")
        for arm in ("de_novo", "crate_only", "healthsheet"):
            self.assertTrue(ARMS[arm][1].startswith("claudecode_agent_"))

    def test_the_directories_are_registered_everywhere_a_method_is_known(self):
        from data_sheets_schema.constants import METHODS
        from data_sheets_schema.runs import AGENT_FAMILY, ARM_BY_METHOD, requires_request
        for m in ("claudecode_api", "claudecode_api_core"):
            self.assertIn(m, METHODS)
            self.assertEqual(ARM_BY_METHOD[m], "baseline")
        self.assertTrue("claudecode_api".startswith(AGENT_FAMILY))
        # the live-provenance requirement reaches the new directory
        self.assertTrue(requires_request("2026-09-20_claude-opus-5-api-generic-v8_rep1", "claudecode_api"))
        self.assertFalse(requires_request("2026-09-20_x_rep1", "rocrate_mapped"))


if __name__ == "__main__":
    unittest.main()
