#!/usr/bin/env python3
"""
Tests for how src/transformation/transform_api.py reads a crate.

#4186: its parsers come from the copy of `ROCrateParser` under
.claude/agents/scripts, which opens a crate as UTF-8 itself, so AI-READI's
windows-1252 release crate ended `merge_rocrates`, and `rocrate_to_d4d`
without input validation, with a bare UnicodeDecodeError. The crate is read
first as `fairscape-cli parse` reads one (`rocrate_map.read_crate_json`),
and refused with a CrateEncodingError that names the first byte that does
not decode and says to transcode the file.
"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data_sheets_schema.rocrate_map import CrateEncodingError
from src.transformation.transform_api import (
    ROCrateParser,
    SemanticTransformer,
    TransformationConfig,
    _parse_rocrate,
)

#: The AI-READI v3.0.0 release crate and its copy among the raw downloads,
#: both windows-1252, not UTF-8 (#4089)
AI_READI = repo_root / "data/ro-crate_packages/AI_READI/raw/ro-crate-metadata.json"
AI_READI_DOWNLOAD = (repo_root / "data/raw/AI_READI/"
                     "aireadi_ro_crate_metadata_2026-08-12.json")
#: A UTF-8 crate
VOICE = repo_root / "data/ro-crate/examples/voice_fairscape_test.json"
#: The mapping the transformer reads, by its absolute path, so that the
#: tests do not depend on the working directory, as the default does
MAPPING = repo_root / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"


def refusal(path):
    """How a tracked AI-READI copy, given by its path, is refused, word for
    word, as `fairscape-cli rocrate-to-d4d`, `info` and `parse` refuse it
    (#4192)."""
    return (f"{path} is not UTF-8, as RFC 8259 requires of JSON: byte 0xa9 at "
            "offset 5096, 31 undecodable byte(s) in all. Not decoded under a "
            "guessed encoding; transcode it to UTF-8 from the encoding it is "
            "written in")


class TestCrateEncoding(unittest.TestCase):
    """#4186: `merge_rocrates` and `rocrate_to_d4d` refuse a crate that is
    not UTF-8 by name. With input validation, the default, `rocrate_to_d4d`
    refuses it earlier, when the validation fails, as it did before."""

    @staticmethod
    def transformer():
        """A transformer that validates nothing; the mapping's progress
        lines are kept off the output."""
        with contextlib.redirect_stdout(io.StringIO()):
            return SemanticTransformer(TransformationConfig(
                mapping_file=MAPPING, validate_input=False, validate_output=False))

    def test_merge_rocrates_and_rocrate_to_d4d_refuse_it_by_name(self):
        """`merge_rocrates` reads a UTF-8 crate first. Neither writes the
        record it was asked for."""
        for path in (AI_READI, AI_READI_DOWNLOAD):
            for given in (path, str(path)):
                calls = {
                    "merge_rocrates": lambda t, out: t.merge_rocrates(
                        [VOICE, given], output_path=out),
                    "rocrate_to_d4d": lambda t, out: t.rocrate_to_d4d(
                        given, output_path=out),
                }
                for name, call in calls.items():
                    with self.subTest(crate=path.name, given=type(given).__name__,
                                      call=name), tempfile.TemporaryDirectory() as tmp:
                        output = Path(tmp) / "record.yaml"
                        transformer = self.transformer()
                        with self.assertRaises(CrateEncodingError) as cm, \
                                contextlib.redirect_stdout(io.StringIO()):
                            call(transformer, output)
                        self.assertEqual(str(cm.exception), refusal(path))
                        self.assertFalse(output.exists())

    def test_a_utf8_crate_and_a_missing_path_reach_the_parser_as_before(self):
        """The crate is read only to refuse it: a UTF-8 crate parses as the
        parser parses it, and a path that is no file is reported by the
        parser, as it was."""
        with contextlib.redirect_stdout(io.StringIO()):
            read, parsed = _parse_rocrate(VOICE), ROCrateParser(str(VOICE))
        self.assertIsInstance(read, ROCrateParser)
        for name in ("rocrate_path", "context", "graph", "root_dataset", "all_properties"):
            with self.subTest(attribute=name):
                self.assertEqual(getattr(read, name), getattr(parsed, name))

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "ro-crate-metadata.json"
            with self.assertRaises(FileNotFoundError) as cm:
                _parse_rocrate(missing)
        self.assertEqual(str(cm.exception), f"RO-Crate file not found: {missing}")


if __name__ == "__main__":
    unittest.main()
