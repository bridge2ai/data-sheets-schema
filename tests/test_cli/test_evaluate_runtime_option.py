"""#690 / #930 review: the `--runtime` option must reach the command that
declares it — both `evaluate` commands raised TypeError on every call when
the decorator sat on the wrong one. Invokes the callbacks, not --help."""
import unittest

from click.testing import CliRunner


class TestTheRuntimeOptionReachesItsCommand(unittest.TestCase):
    def _invoke(self, *args):
        from data_sheets_schema.cli.evaluate import evaluate
        return CliRunner().invoke(evaluate, list(args))

    def test_verifiable_runs_its_callback(self):
        out = self._invoke("verifiable", "--label", "no-such-label-xyz", "--project", "CHORUS")
        self.assertNotIsInstance(out.exception, TypeError, out.output)

    def test_related_datasets_takes_runtime(self):
        out = self._invoke("related-datasets", "--runtime", "api", "--project", "CHORUS")
        self.assertNotIsInstance(out.exception, TypeError, out.output)
        self.assertNotIn("No such option", out.output)

    def test_plan_takes_runtime_and_names_the_remedy_once(self):
        out = self._invoke("plan", "--runtime", "api", "--paths-only")
        self.assertNotIsInstance(out.exception, TypeError, out.output)
        out = self._invoke("plan", "--paths-only")
        if out.exit_code:
            self.assertEqual(out.output.count("Pass "), 1, out.output)


if __name__ == "__main__":
    unittest.main()
