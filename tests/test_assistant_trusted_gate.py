"""#4392: execute the workflow gate with a fake API and isolated real parser.

All GitHub replies and candidate files are owned synthetic fixtures. No API or
provider request is made; the JavaScript is the actual workflow step body.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/d4d-agent.yml"
PARSER = ROOT / "src/github/assistant_request.py"
BASE = "a" * 40
DEFAULT = "b" * 40
HEAD = "c" * 40
HANDLE = "@d4dassistant"

# The only API surface is this explicit fake. Calls and actual step outputs
# are retained in the result, including when trusted retrieval refuses.
NODE_HARNESS = r'''
const fs = require('fs');
const crypto = require('crypto');
const assert = require('assert');
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const result = {calls: [], outputs: {}, error: null};
const repo = {owner: 'fixture-owner', repo: 'fixture-repo'};
function record(method, args) { result.calls.push({method, args}); }
const github = {rest: {
  repos: {
    get: async args => {record('repos.get', args); assert.deepStrictEqual(args, repo); return {data: {default_branch: 'main'}};},
    getBranch: async args => {record('repos.getBranch', args); assert.deepStrictEqual(args, {...repo, branch: 'main'}); return {data: {commit: {sha: input.defaultSha}}};},
    getContent: async args => {
      record('repos.getContent', args);
      assert.deepStrictEqual(args, {...repo, path: args.path, ref: input.expectedSha});
      assert(['.github/ai-controllers.json', 'src/github/assistant_request.py'].includes(args.path));
      if (!Object.prototype.hasOwnProperty.call(input.files, args.path)) throw new Error('Trusted file missing');
      const bytes = Buffer.from(input.files[args.path], 'utf8');
      const data = {type: 'file', path: args.path, encoding: 'base64', size: bytes.length,
        content: bytes.toString('base64'), sha: crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex')};
      Object.assign(data, (input.responseChanges || {})[args.path] || {});
      return {data};
    }
  },
  issues: {
    get: async args => {record('issues.get', args); return {data: {body: input.body}};},
    listComments: async args => {
      record('issues.listComments', args);
      assert.deepStrictEqual(args, {...repo, issue_number: 7, per_page: 100, page: args.page});
      if (input.pageError === args.page) throw new Error('Owned page retrieval failure');
      if (input.pageOverrides && Object.prototype.hasOwnProperty.call(input.pageOverrides, args.page))
        return {data: input.pageOverrides[args.page]};
      return {data: input.comments.slice((args.page-1)*100, args.page*100)};
    }
  },
  pulls: {get: async args => {record('pulls.get', args); return {data: {body: input.body, base: {sha: input.baseSha}, head: {sha: input.headSha}}};}}
}};
const core = {setOutput: (name, value) => {result.outputs[name] = value;}};
const context = {...input.context, repo};
(async () => {
  try {
    const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
    await new AsyncFunction('github', 'context', 'core', 'require', input.script)(github, context, core, require);
  } catch (error) { result.error = {type: error.name, message: error.message}; }
  fs.writeFileSync(process.argv[3], JSON.stringify(result));
})().catch(error => { console.error(error); process.exitCode = 1; });
'''


class _GateFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            raise RuntimeError("Node is required to test the actual actions/github-script gate")
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        steps = {step.get("id"): step for step in workflow["jobs"]["check-mention"]["steps"]}
        cls.detect = steps["detect"]["with"]["script"]
        cls.request = steps["request"]
        cls.parser = PARSER.read_text(encoding="utf-8")

    def _fixture(self, directory, *, event="pull_request", actor="trusted-user", body=None,
                 missing=None, base=BASE, default=DEFAULT, changes=None, controllers=None, content_author=None,
                 event_data=None, comments=None, page_error=None, page_overrides=None, parser_text=None):
        tmp = Path(directory)
        candidate = tmp / "candidate"
        candidate.mkdir()
        (candidate / ".github").mkdir()
        (candidate / ".github/ai-controllers.json").write_text('["candidate-attacker"]')
        scripts = candidate / "src/github"
        scripts.mkdir(parents=True)
        (scripts / "assistant_request.py").write_text('raise SystemExit("candidate parser executed")\n')
        inputs = candidate / "data/sheets_d4dassistant/inputs"
        (inputs / "BranchOnly").mkdir(parents=True)
        (inputs / "BranchOther").mkdir()
        # Both cwd imports and PYTHONPATH/site initialization must be ignored.
        for name in ("pathlib.py", "sitecustomize.py"):
            (candidate / name).write_text('raise RuntimeError("candidate import executed")\n')
        runtime = tmp / "runner"
        runtime.mkdir()
        python_bin = self._python(runtime)
        body = body if body is not None else f"{HANDLE} BranchOnly"
        author = actor if content_author is None else content_author
        payload = {"pull_request": {"base": {"sha": base}, "head": {"sha": HEAD},
                                    "body": body, "user": {"login": author}, "number": 7},
                   "issue": {"body": body, "user": {"login": author}, "number": 7},
                   "comment": {"body": body, "user": {"login": author}},
                   "inputs": {"item-type": "pull_request", "item-number": "7"}}
        payload.update(event_data or {})
        context = {"eventName": event, "actor": actor, "payload": payload}
        files = {".github/ai-controllers.json": json.dumps(controllers if controllers is not None else ["trusted-user"]),
                 "src/github/assistant_request.py": self.parser if parser_text is None else parser_text}
        if missing:
            del files[missing]
        expected = base if event in ("pull_request", "pull_request_review_comment") else default
        fixture = {"context": context, "files": files, "script": self.detect, "expectedSha": expected,
                   "defaultSha": default, "baseSha": base, "headSha": HEAD, "body": body,
                   "responseChanges": changes or {}, "comments": comments or [],
                   "pageError": page_error, "pageOverrides": page_overrides or {}}
        control, input_path, output = tmp / "control.js", tmp / "input.json", tmp / "result.json"
        control.write_text(NODE_HARNESS)
        input_path.write_text(json.dumps(fixture))
        result = subprocess.run([self.node, str(control), str(input_path), str(output)], cwd=candidate,
                                env={**os.environ, "RUNNER_TEMP": str(runtime), "PYTHONPATH": str(candidate),
                                     "PATH": str(python_bin) + os.pathsep + os.environ.get("PATH", "")},
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(output.read_text()), candidate, runtime

    @staticmethod
    def _python(runtime):
        binary = runtime.parent / "python-bin"
        binary.mkdir(exist_ok=True)
        executable = binary / "python3"
        executable.write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "$@"\n')
        executable.chmod(0o755)
        return binary

    def _run_request(self, result, candidate, runtime):
        self.assertIsNone(result["error"])
        self.assertIs(result["outputs"]["allowed"], True)
        parser = Path(result["outputs"]["gate-parser"])
        self.assertTrue(parser.is_relative_to(runtime))
        self.assertEqual(parser.read_bytes(), PARSER.read_bytes())
        self.assertFalse((parser.parent / "data").exists())
        binary = self._python(runtime)
        output = runtime / "github-output"
        run = subprocess.run(["bash", "-c", self.request["run"]], cwd=candidate,
                             env={**os.environ, "PATH": str(binary) + os.pathsep + os.environ.get("PATH", ""),
                                  "PYTHONPATH": str(candidate), "RUNNER_TEMP": str(runtime),
                                  "TRUSTED_REQUEST_PARSER": str(parser), "GITHUB_OUTPUT": str(output)},
                             capture_output=True, text=True, timeout=20)
        return run, output

    def _request(self, result, candidate, runtime):
        run, output = self._run_request(result, candidate, runtime)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, "")
        return output.read_text(), run.stdout


class TestTrustedAssistantGate(_GateFixture):
    def test_pr_base_gate_accepts_branch_only_input_despite_candidate_poison(self):
        with tempfile.TemporaryDirectory() as directory:
            result, candidate, runtime = self._fixture(directory)
            self.assertEqual(result["outputs"]["gate-base-sha"], BASE)
            calls = result["calls"]
            self.assertEqual([call["method"] for call in calls], ["repos.getContent", "repos.getContent"])
            self.assertEqual({call["args"]["path"] for call in calls},
                             {".github/ai-controllers.json", "src/github/assistant_request.py"})
            self.assertEqual({call["args"]["ref"] for call in calls}, {BASE})
            output, _ = self._request(result, candidate, runtime)
            self.assertEqual(output, "request=true\ndataset=BranchOnly\n")

    def test_candidate_allow_list_cannot_authorize_its_own_actor(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _, _ = self._fixture(directory, actor="candidate-attacker")
            self.assertIsNone(result["error"])
            self.assertIs(result["outputs"]["allowed"], False)
            self.assertEqual(result["outputs"]["controllers"], "@trusted-user")

    def test_trusted_parser_still_refuses_hidden_or_quoted_requests(self):
        for body in (f"`{HANDLE} BranchOnly`", f"<video>\n\n{HANDLE} BranchOnly\n\n</video>"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(directory, body=body)
                output, _ = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=false\ndataset=\n")

    def test_pr_review_and_default_manual_resolution_preserve_author_policy(self):
        for event in ("pull_request_review_comment", "issues", "issue_comment", "workflow_dispatch"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                result, _, _ = self._fixture(directory, event=event)
                self.assertIsNone(result["error"])
                expected = BASE if event == "pull_request_review_comment" else DEFAULT
                self.assertEqual(result["outputs"]["gate-base-sha"], expected)
                self.assertEqual(result["outputs"]["user"], "trusted-user")
                self.assertIs(result["outputs"]["allowed"], True)
                files = [call for call in result["calls"] if call["method"] == "repos.getContent"]
                self.assertEqual(len(files), 2)
                self.assertEqual({call["args"]["ref"] for call in files}, {expected})
                defaults = [call["method"] for call in result["calls"] if call["method"] in ("repos.get", "repos.getBranch")]
                self.assertEqual(defaults, [] if expected == BASE else ["repos.get", "repos.getBranch"])

    def test_manual_actor_and_event_content_author_choices_remain_distinct(self):
        for event in ("workflow_dispatch", "issues", "issue_comment", "pull_request", "pull_request_review_comment"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                result, _, _ = self._fixture(directory, event=event, actor="trusted-user",
                                             content_author="candidate-attacker")
                self.assertIsNone(result["error"])
                self.assertEqual(result["outputs"]["user"],
                                 "trusted-user" if event == "workflow_dispatch" else "candidate-attacker")
                self.assertIs(result["outputs"]["allowed"], event == "workflow_dispatch")

    def test_missing_trusted_file_fails_closed_without_candidate_fallback(self):
        for missing in ("src/github/assistant_request.py", ".github/ai-controllers.json"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                result, _, runtime = self._fixture(directory, missing=missing)
                self.assertIn("Trusted file missing", result["error"]["message"])
                self.assertNotIn("allowed", result["outputs"])
                self.assertEqual(list(runtime.iterdir()), [])

    def test_invalid_immutable_commit_never_fetches_gate_files(self):
        for event, args in (("pull_request", {"base": "main"}), ("pull_request", {"base": None}),
                            ("workflow_dispatch", {"default": HEAD[:39]})):
            with self.subTest(event=event, args=args), tempfile.TemporaryDirectory() as directory:
                result, _, _ = self._fixture(directory, event=event, **args)
                self.assertIn("immutable trusted base", result["error"]["message"])
                self.assertFalse(any(call["method"] == "repos.getContent" for call in result["calls"]))
                self.assertNotIn("allowed", result["outputs"])

    def test_trusted_file_integrity_and_allow_list_shape_refuse(self):
        changes = ({"sha": "0" * 40}, {"size": 0}, {"encoding": "none"}, {"path": "elsewhere"},
                   {"type": "dir"}, {"content": "not base64!"})
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                result, _, runtime = self._fixture(directory, changes={"src/github/assistant_request.py": change})
                self.assertIsNotNone(result["error"])
                self.assertNotIn("allowed", result["outputs"])
                self.assertEqual(list(runtime.iterdir()), [])
        for controllers in ({"trusted-user": True}, ["trusted-user", 1]):
            with self.subTest(controllers=controllers), tempfile.TemporaryDirectory() as directory:
                result, _, _ = self._fixture(directory, controllers=controllers)
                self.assertIn("array of usernames", result["error"]["message"])
                self.assertNotIn("allowed", result["outputs"])

    def test_request_step_uses_only_trusted_path_in_isolated_mode(self):
        self.assertEqual(self.request["env"], {"TRUSTED_REQUEST_PARSER": "${{ steps.detect.outputs.gate-parser }}"})
        self.assertIn('python3 -I -S "$TRUSTED_REQUEST_PARSER"', self.request["run"])
        self.assertIn('--inputs data/sheets_d4dassistant/inputs', self.request["run"])
        self.assertNotIn('python3 src/github/assistant_request.py', self.request["run"])


class TestRequestSelection(_GateFixture):
    EVENTS = ("issues", "issue_comment", "pull_request", "pull_request_review_comment")
    REQUEST = f"{HANDLE} BranchOnly"

    def _edited(self, before, after, event="issues"):
        with tempfile.TemporaryDirectory() as directory:
            result, candidate, runtime = self._fixture(
                directory, event=event, body=after,
                event_data={"action": "edited", "changes": {"body": {"from": before}}})
            return self._request(result, candidate, runtime)

    def test_unrelated_edits_do_not_repeat_any_event_request(self):
        for event in self.EVENTS:
            with self.subTest(event=event):
                output, log = self._edited(self.REQUEST, "New surrounding prose.\n\n" + self.REQUEST, event)
                self.assertEqual(output, "request=false\ndataset=\n")
                self.assertIn("same parsed request", log)

    def test_spelling_line_and_same_dataset_duplicates_are_not_new_requests(self):
        for after in ("@D4DASSISTANT\tBranchOnly  ", "\n\n" + self.REQUEST,
                      self.REQUEST + "\n\n" + self.REQUEST):
            with self.subTest(after=after):
                output, _ = self._edited(self.REQUEST, after)
                self.assertEqual(output, "request=false\ndataset=\n")

    def test_new_changed_or_newly_visible_request_qualifies(self):
        other = f"{HANDLE} BranchOther"
        for before, after, dataset in (
                ("No request yet", self.REQUEST, "BranchOnly"),
                (self.REQUEST, other, "BranchOther"),
                (f"<video>\n\n{self.REQUEST}\n\n</video>", self.REQUEST, "BranchOnly"),
                (f"`{self.REQUEST}`", self.REQUEST, "BranchOnly"),
                (self.REQUEST + "\n\n" + other, self.REQUEST, "BranchOnly")):
            with self.subTest(before=before, after=after):
                output, _ = self._edited(before, after)
                self.assertEqual(output, f"request=true\ndataset={dataset}\n")

    def test_removed_hidden_unknown_or_conflicting_after_text_never_qualifies(self):
        for after in ("Removed", f"<rp>\n\n{self.REQUEST}\n\n</rp>",
                      f"{HANDLE} Missing", self.REQUEST + f"\n\n{HANDLE} BranchOther"):
            with self.subTest(after=after):
                output, _ = self._edited(self.REQUEST, after)
                self.assertEqual(output, "request=false\ndataset=\n")

    def test_title_or_other_edits_without_body_history_skip(self):
        for event in self.EVENTS:
            for changes in ({}, {"title": {"from": "old"}}, None):
                with self.subTest(event=event, changes=changes), tempfile.TemporaryDirectory() as directory:
                    result, candidate, runtime = self._fixture(
                        directory, event=event, event_data={"action": "edited", "changes": changes})
                    output, log = self._request(result, candidate, runtime)
                    self.assertEqual(output, "request=false\ndataset=\n")
                    self.assertIn("no body change", log)

    def test_malformed_edit_history_fails_closed_before_request_step(self):
        for changes in ([], "invalid", {"body": None}, {"body": {}},
                        {"body": {"from": None}}, {"body": {"from": []}}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as directory:
                result, _, runtime = self._fixture(
                    directory, event_data={"action": "edited", "changes": changes})
                self.assertIsNotNone(result["error"])
                self.assertNotIn("allowed", result["outputs"])
                self.assertFalse((runtime / "assistant-request-selection.json").exists())

    def test_created_events_keep_the_original_request_behavior(self):
        for event in self.EVENTS:
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(directory, event=event,
                                                          event_data={"action": "created"})
                output, _ = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=true\ndataset=BranchOnly\n")

    def test_manual_valid_body_wins_without_fetching_comments(self):
        for body in (self.REQUEST, "@D4DASSISTANT BranchOnly"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(
                    directory, event="workflow_dispatch", body=body,
                    comments=[{"id": 1, "body": f"{HANDLE} BranchOther"}],
                    page_error=1, event_data={"action": "edited", "changes": {"body": {"from": body}}})
                output, _ = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=true\ndataset=BranchOnly\n")
                self.assertFalse(any(c["method"] == "issues.listComments" for c in result["calls"]))

    def test_manual_newer_nonrequests_do_not_hide_older_actual_request(self):
        newer = (f"`{self.REQUEST}`", f"```\n{self.REQUEST}\n```",
                 f"<video>\n\n{self.REQUEST}\n\n</video>", f"{HANDLE} Missing",
                 self.REQUEST + f"\n\n{HANDLE} BranchOther")
        for text in newer:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(
                    directory, event="workflow_dispatch", body=f"`{self.REQUEST}`",
                    comments=[{"id": 1, "body": "@D4DASSISTANT BranchOther"}, {"id": 2, "body": text}])
                output, log = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=true\ndataset=BranchOther\n")
                self.assertIn("conversation comment 1", log)

    def test_manual_pagination_selects_newest_valid_request_across_all_pages(self):
        comments = [{"id": i, "body": "ordinary prose"} for i in range(1, 202)]
        comments[0]["body"] = self.REQUEST
        comments[100]["body"] = f"{HANDLE} BranchOther"
        comments[200]["body"] = f"`{self.REQUEST}`"
        for item_type in ("issue", "pull_request"):
            with self.subTest(item_type=item_type), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(
                    directory, event="workflow_dispatch", body="No body request", comments=comments,
                    event_data={"inputs": {"item-type": item_type, "item-number": "7"}})
                output, log = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=true\ndataset=BranchOther\n")
                self.assertIn("conversation comment 101", log)
                self.assertEqual([c["args"]["page"] for c in result["calls"]
                                  if c["method"] == "issues.listComments"], [1, 2, 3])

    def test_manual_creation_order_and_actor_policy_stay_unchanged(self):
        comments = [
            {"id": 1, "body": self.REQUEST, "updated_at": "2099-01-01T00:00:00Z"},
            {"id": 2, "body": f"{HANDLE} BranchOther", "updated_at": "2000-01-01T00:00:00Z",
             "user": {"login": "candidate-attacker"}}]
        with tempfile.TemporaryDirectory() as directory:
            result, candidate, runtime = self._fixture(
                directory, event="workflow_dispatch", body="No request", comments=comments,
                actor="trusted-user", content_author="candidate-attacker")
            output, log = self._request(result, candidate, runtime)
            self.assertEqual(output, "request=true\ndataset=BranchOther\n")
            self.assertEqual(result["outputs"]["user"], "trusted-user")
            self.assertIn("conversation comment 2", log)

    def test_manual_comments_are_separate_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            result, candidate, runtime = self._fixture(
                directory, event="workflow_dispatch", body="No request",
                comments=[{"id": 1, "body": "```"}, {"id": 2, "body": self.REQUEST}])
            output, _ = self._request(result, candidate, runtime)
            self.assertEqual(output, "request=true\ndataset=BranchOnly\n")

    def test_manual_no_valid_candidate_has_no_request(self):
        for comments in ([], [{"id": 1, "body": None}, {"id": 2, "body": f"`{self.REQUEST}`"}]):
            with self.subTest(comments=comments), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(
                    directory, event="workflow_dispatch", body="No request", comments=comments)
                output, _ = self._request(result, candidate, runtime)
                self.assertEqual(output, "request=false\ndataset=\n")

    def test_partial_or_malformed_comment_pages_fail_closed(self):
        comments = [{"id": i, "body": self.REQUEST if i == 1 else "prose"} for i in range(1, 101)]
        variants = ({"comments": comments, "page_error": 2}, {"page_overrides": {"1": {}}},
                    {"comments": [{"id": 1, "body": self.REQUEST}, {"id": 1, "body": self.REQUEST}]},
                    {"comments": [{"id": True, "body": self.REQUEST}]},
                    {"comments": [{"id": 1, "body": []}]})
        for options in variants:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                result, _, runtime = self._fixture(directory, event="workflow_dispatch", body="No request", **options)
                self.assertIsNotNone(result["error"])
                self.assertNotIn("allowed", result["outputs"])
                self.assertFalse((runtime / "assistant-request-selection.json").exists())

    def test_unaware_or_malformed_trusted_body_probe_never_falls_back_to_candidate(self):
        parsers = ("import argparse\nargparse.ArgumentParser().parse_args()\n",
                   'print(\'{"request":"true","dataset":"BranchOnly","line":1}\')\n',
                   'print(\'{"request":false}\')\n')
        for parser in parsers:
            with self.subTest(parser=parser), tempfile.TemporaryDirectory() as directory:
                result, _, runtime = self._fixture(directory, event="workflow_dispatch", parser_text=parser)
                self.assertIsNotNone(result["error"])
                self.assertNotIn("allowed", result["outputs"])
                self.assertFalse((runtime / "assistant-request-selection.json").exists())

    def test_malformed_selection_file_refuses_even_with_valid_body(self):
        invalid = ('[]', '{"kind":"unknown"}', '{"kind":"single","extra":true}',
                   '{"kind":"edited"}', '{"kind":"edited","before":null}',
                   '{"kind":"manual","comments":null}',
                   '{"kind":"manual","comments":[{"id":true,"body":""}]}',
                   '{"kind":"manual","comments":[{"id":1,"body":""},{"id":1,"body":""}]}',
                   '{"kind":"single","kind":"unchanged"}', '{"kind":"edited","before":NaN}', '{')
        for raw in invalid:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                result, candidate, runtime = self._fixture(directory)
                (runtime / "assistant-request-selection.json").write_text(raw)
                run, output = self._run_request(result, candidate, runtime)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("invalid request selection", run.stderr)
                self.assertFalse(output.exists())
