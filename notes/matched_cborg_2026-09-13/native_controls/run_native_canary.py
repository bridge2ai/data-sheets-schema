"""Draft single native generation canary, requiring a separately reviewed overlay."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from budgeted_cborg import BudgetStop, open_ledger, attempt_identity, write_new
from budgeted_cborg import cborg_client, provider_context_headers, provider_context_evidence
from native_proxy import NativeProxy
from prepare_registration import spec_for
from run_api_canary import verify, verify_history, sha, check_canary_receipts
from prepare_overlay_roster import PLAYBOOK_COMMANDS, MODULE_ENTRY_POINTS
from native_command_policy import command_guidance, permission_arguments, program_key, validated_command_policy
from native_readonly import lookup_command, registered_input_paths


def now():
    return datetime.now(timezone.utc).isoformat()


def verified_executable(overlay):
    path = Path(overlay['claude_executable'])
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise BudgetStop('native executable must be an absolute resolved path')
    if overlay['pinned_files'].get(str(path)) != sha(path):
        raise BudgetStop('native executable bytes differ from the launch pin')
    return str(path)


#: Characters bash reads as control or redirection operators when they are
#: unquoted, alone or merged (`>|`, `&>>`, `<>`, `)|`). The system prompt
#: forbids chaining unlisted programs, heredocs and writes outside the output
#: directories, and no command the instruction prescribes uses any of them.
OPERATOR_CHARS = frozenset(';&|<>()')


def _shell_tokens(command, bash_words=False):
    """shlex words. With bash_words, for text `_simple_command` has already
    scanned: no comment character, and only a space or tab separates words
    (bash keeps a carriage return inside the word)."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        if bash_words:
            lexer.commenters = ''
            lexer.whitespace = ' \t'
        return list(lexer)
    except ValueError:
        return None


FORBIDDEN_SHELL = 'shell operators, redirection or substitution the system prompt forbids'


def _simple_command(command):
    """The command's words when bash would read one simple command, else
    (None, reason).

    shlex alone does not see how bash splits a command line (#2031): with
    whitespace_split a newline is whitespace, a run of operator characters is
    one token, and a `#` inside a word hides the rest of the line. So the
    text is scanned first with bash's quoting. A backslash-newline joins two
    lines. A `#` starts a comment only at the start of a word. A newline
    ends the command, so any word after it, outside a comment, is a second
    command. An unquoted operator character, a backtick or `$(` (also inside
    double quotes) means the text is not one simple command."""
    out = []
    quote = None
    word_start = True
    ended = False
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote == "'":
            out.append(ch)
            quote = None if ch == "'" else quote
            i += 1
            continue
        if ch == '\\' and command[i + 1:i + 2] == '\n':
            i += 2
            continue
        if quote is None:
            if ch in ' \t':
                out.append(ch)
                word_start = True
                i += 1
                continue
            if ch == '\n':
                ended = ended or bool(''.join(out).strip())
                out.append(' ')
                word_start = True
                i += 1
                continue
            if ch == '#' and word_start:
                end = command.find('\n', i)
                i = n if end < 0 else end
                continue
            if ended:
                return None, FORBIDDEN_SHELL
        if ch == '`' or command.startswith('$(', i):
            return None, FORBIDDEN_SHELL
        if ch == '\\':
            out.append(command[i:i + 2])
            word_start = False
            i += 2
            continue
        if quote == '"':
            out.append(ch)
            quote = None if ch == '"' else quote
            i += 1
            continue
        if ch in OPERATOR_CHARS:
            return None, FORBIDDEN_SHELL
        if ch in '\'"':
            quote = ch
        out.append(ch)
        word_start = False
        i += 1
    tokens = None if quote else _shell_tokens(''.join(out), bash_words=True)
    if not tokens:
        return None, 'shell text that does not parse'
    return tokens, None


def _roster_command(args):
    """The roster command `args` begins with, matched word by word (a roster
    command may have three words: `api prompts check`)."""
    for command in sorted(PLAYBOOK_COMMANDS, key=lambda c: -len(c.split())):
        words = command.split()
        if args[:len(words)] == words:
            return command
    return None


def prescribed_programs(instruction_text, python):
    """The `python -c` programs the rendered instruction prescribes verbatim
    (the validators and the multi-line original-freeze command). A command
    spanning several lines is read until its quoting closes."""
    programs = set()
    head = f'{python} -c '
    start = 0
    while True:
        at = instruction_text.find(head, start)
        if at < 0:
            return programs
        end = instruction_text.find('\n', at)
        tokens = None
        while True:
            tokens = _shell_tokens(instruction_text[at:end if end >= 0 else len(instruction_text)])
            if tokens is not None or end < 0:
                break
            end = instruction_text.find('\n', end + 1)
        if tokens and len(tokens) > 2:
            programs.add(tokens[2].strip())
        start = at + 1


def _classify_command(command, python, programs, command_policy=None):
    if lookup_command(command, (command_policy or {}).get('readonly_lookups'), _simple_command):
        return 'prescribed', 'a registered read-only lookup of this job\'s inputs or outputs'
    tokens, reason = _simple_command(command)
    if tokens is None:
        return 'not_prescribed', reason
    if tokens[0] != python or len(tokens) < 3:
        return 'not_prescribed', 'a program the instruction does not prescribe'
    rest = tokens[3:] if tokens[1] == '-c' else tokens[1:]
    if any(t in ('--help', '-h') for t in rest):
        return 'not_prescribed', '--help exploration the system prompt forbids'
    if tokens[1] == '-c':
        if command_policy is not None:
            try:
                key = program_key(tokens[2])
            except (SyntaxError, ValueError, TypeError):
                return 'not_prescribed', 'an invalid inline Python program'
            for program in command_policy['programs']:
                if key == program_key(program['code']):
                    if tokens[3:] and not program['arguments']:
                        return 'not_prescribed', 'extra arguments to a fixed registered program'
                    return 'prescribed', 'a Python program from the registered instruction or selected playbook'
            return 'not_prescribed', 'an ad-hoc -c script the system prompt forbids'
        if tokens[2].strip() in programs:
            return 'prescribed', 'a -c program the instruction prescribes verbatim'
        return 'not_prescribed', 'an ad-hoc -c script the system prompt forbids'
    if tokens[1] != '-m':
        return 'not_prescribed', 'an interpreter form the instruction does not prescribe'
    module = tokens[2]
    if module == 'data_sheets_schema.cli':
        args = tokens[3:]
        if args[:1] == ['--manifest']:
            if command_policy is not None and (len(args) < 2 or args[1] not in command_policy['manifest_paths']):
                return 'not_prescribed', 'a manifest outside the registered job'
            args = args[2:]
        roster = _roster_command(args)
        if roster:
            return 'prescribed', f"the roster command '{roster}'"
        return 'not_prescribed', 'a CLI command outside the prescribed roster'
    if module.startswith('data_sheets_schema.') and module.split('.', 1)[1] in MODULE_ENTRY_POINTS:
        return 'prescribed', f"the registered module entry point '{module}'"
    return 'not_prescribed', 'a module the instruction does not prescribe'


def _classify_path(tool, path, repository, output_directories, readable_inputs):
    if not path:
        return 'not_prescribed', 'a file operation without a path'
    def resolved(value):
        candidate = Path(value)
        return (candidate if candidate.is_absolute() else Path(repository) / candidate).resolve()
    target = resolved(path)
    for folder in output_directories or ():
        if target == resolved(folder) or resolved(folder) in target.parents:
            return 'prescribed', 'a file inside the registered output directories'
    if tool == 'Read' and any(target == resolved(x) for x in readable_inputs or () if x):
        return 'prescribed', 'a registered input the instruction reads'
    return 'not_prescribed', 'a path outside the registered inputs and outputs'


def classify_denials(denials, *, instruction_text, python, repository, output_directories, readable_inputs,
                    command_policy=None):
    """Every tool-permission denial, listed and classified (#2012, #2026).

    The maintainer ruled (2026-09-17) that a denied prescribed command
    disqualifies a run while denials of forbidden commands are listed and do
    not disqualify it on their own. A denial is prescribed when the controls
    should have allowed it: a roster CLI command, a registered module entry
    point, one of the registered instruction/playbook's `-c` programs, or a file operation
    inside the registered outputs (or a Read of a registered input), with no
    shell operator and no --help, or a bounded read-only lookup including its
    permitted pipes. A denial record the runtime wrote in an
    unexpected shape (no tool name, a Bash record without a command, a file
    record without a path, a path that cannot be resolved) is unclassifiable
    and disqualifies like a prescribed one: nothing shows it was harmless."""
    if denials in (None, []):
        return []
    if not isinstance(denials, list):
        return [{'classification': 'unclassifiable', 'basis': 'permission_denials is not a list'}]
    programs = prescribed_programs(instruction_text, python)
    out = []
    for item in denials:
        if not isinstance(item, dict) or not isinstance(item.get('tool_input'), dict):
            out.append({'classification': 'unclassifiable', 'basis': 'a denial record without tool_input'})
            continue
        tool = item.get('tool_name'); tool_input = item['tool_input']
        if not isinstance(tool, str) or not tool:
            out.append({'classification': 'unclassifiable', 'basis': 'a denial record without a tool name'})
            continue
        entry = {'tool': tool, 'tool_use_id': item.get('tool_use_id')}
        if tool == 'Bash':
            command = tool_input.get('command')
            if not isinstance(command, str):
                entry['classification'], entry['basis'] = 'unclassifiable', 'a Bash denial without a command'
            elif not command.strip():
                # A blank command is well formed and harmless, and no
                # instruction prescribes it (#2036).
                entry['command'] = command
                entry['classification'], entry['basis'] = 'not_prescribed', 'an empty command'
            else:
                entry['command'] = command[:1000]
                entry['classification'], entry['basis'] = _classify_command(command, python, programs, command_policy)
        elif tool in ('Read', 'Write', 'Edit'):
            path = tool_input.get('file_path')
            if not isinstance(path, str) or not path:
                entry['classification'], entry['basis'] = 'unclassifiable', f'a {tool} denial without a file path'
            else:
                entry['path'] = path
                try:
                    entry['classification'], entry['basis'] = _classify_path(
                        tool, path, repository, output_directories, readable_inputs)
                except (OSError, ValueError, UnicodeError):
                    entry['classification'], entry['basis'] = 'unclassifiable', 'a path the controller cannot resolve'
        else:
            entry['classification'], entry['basis'] = 'not_prescribed', 'a tool the registration does not grant'
        out.append(entry)
    return out


def registered_reads(job):
    """The files the job's instruction has the run read: the bundle, the
    chunk map, the source manifest, the instruction itself, the two schemas
    and the playbooks the instruction reaches (the guard, the playbook, the
    uniform rules and the agent file; provenance.AGENT_PLAYBOOKS, which a
    test holds equal to that closure). The toolchain's resource map also
    inventories every other agent definition, evaluation rubrics included;
    those are hashed, not read, so they are not registered reads (#2039)."""
    return registered_input_paths(job)


def command_history(events, command_policy, denials):
    """Check every observed Bash call, including nonzero command exits.

    A denied call did not execute and retains the maintainer's separate denial
    policy. A tool error by itself does not prove denial or lack of side effects.
    This audit checks command conformance, not whether required steps happened.
    """
    denied = {d.get('tool_use_id') for d in denials if isinstance(d, dict)}
    calls = []
    results = {}
    result_errors = {}
    problems = []
    for line, event in enumerate(events, 1):
        message = event.get('message')
        if not isinstance(message, dict) or not isinstance(message.get('content'), list):
            continue
        for block in message['content']:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                calls.append((line, block))
            elif block.get('type') == 'tool_result':
                results.setdefault(block.get('tool_use_id'), []).append(line)
                result_errors.setdefault(block.get('tool_use_id'), []).append(block.get('is_error'))
    checked = []
    seen = set()
    for line, call in calls:
        identity = call.get('id')
        if not isinstance(identity, str) or not identity or identity in seen:
            problems.append(f'Bash call at transcript line {line} has missing or duplicate identity')
            continue
        seen.add(identity)
        entry = {'tool_use_id': identity, 'call_line': line, 'result_lines': results.get(identity, [])}
        if identity in denied:
            entry['classification'] = 'denied_not_executed'
            if result_errors.get(identity) != [True]:
                problems.append(f'Bash denial at transcript line {line} lacks one matching error result')
        else:
            payload = call.get('input')
            command = payload.get('command') if isinstance(payload, dict) else None
            if not isinstance(command, str) or not command.strip():
                entry.update(classification='unclassifiable', basis='missing or empty Bash command')
            else:
                classification, basis = _classify_command(command, command_policy['python'], set(), command_policy)
                entry.update(classification=classification, basis=basis, command=command[:1000])
            if entry['classification'] != 'prescribed':
                problems.append(f'nonconforming executed Bash call at transcript line {line}: {entry["basis"]}')
        if len(entry['result_lines']) != 1 or entry['result_lines'][0] <= line:
            problems.append(f'Bash call at transcript line {line} lacks one subsequent tool result')
        checked.append(entry)
    return {'checked': True, 'calls': checked, 'problems': problems}


STOPPED_DENIALS_NOTE = ('not classified: the transcript holds no single readable runtime result line; '
                        "the transcript's tool history is the source")


def stopped_denials(path, classify):
    """The denial classification for a stopped attempt (#2032, #2037).

    The completed path classifies the result line it has already read. A
    stopped attempt may still have one: a ledger or proxy refusal ends in the
    runtime's error result, and an init mismatch stops before classification.
    So the stop path reads the transcript itself and classifies the one
    result line it holds; with none (a deadline stop) or more than one, it
    says it classified nothing. Never raises: a diagnostic must not displace
    the stop it describes."""
    try:
        results = []
        with Path(path).open('rb') as fh:
            for raw in fh:
                try:
                    event = json.loads(raw.decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    continue
                if isinstance(event, dict) and event.get('type') == 'result':
                    results.append(event)
        if len(results) != 1:
            note = STOPPED_DENIALS_NOTE if not results else (
                f'not classified: the transcript holds {len(results)} runtime result lines; '
                "the transcript's tool history is the source")
            return {'permission_denials_note': note}
        classified = classify(results[0].get('permission_denials'))
        return {'permission_denials': classified, 'disqualifying_denials': denial_problems(classified)}
    except Exception as error:
        return {'permission_denials_note': f'not classified: {type(error).__name__} while reading the transcript; '
                                           "the transcript's tool history is the source"}


def denial_problems(classified):
    """The denials that disqualify a run under the maintainer's ruling."""
    return [f"denied {d['classification']} call ({d.get('tool') or 'unknown tool'}): {d['basis']}"
            for d in classified if d.get('classification') in ('prescribed', 'unclassifiable')]


def transcript_terminal_state(path):
    """Whether the runtime's stream-json transcript reached its terminal
    result line (#2014). A child stopped at the deadline never writes one, so
    the transcript's token figures are per-message snapshots and the ledger is
    the attempt's accounting; the receipt says so rather than leaving it to be
    inferred. Never raises (#2019): a transcript cut mid-write can hold
    undecodable bytes, and a diagnostic must not displace the stop it
    describes."""
    try:
        with Path(path).open('rb') as fh:
            for raw in fh:
                try:
                    event = json.loads(raw.decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    continue
                if isinstance(event, dict) and event.get('type') == 'result':
                    return {'transcript_terminal_result': 'present'}
    except FileNotFoundError:
        return {'transcript_terminal_result': 'missing',
                'transcript_accounting_note': 'no transcript was written; the ledger is this attempt\'s accounting'}
    except Exception as error:
        return {'transcript_terminal_result': 'unreadable', 'transcript_read_note': type(error).__name__}
    return {'transcript_terminal_result': 'absent',
            'transcript_accounting_note': 'no runtime result line: transcript token figures are per-message '
                                          'snapshots; the ledger is this attempt\'s accounting'}


def record_controller_stop(ledger, billing_attempt, receipt):
    """Record the stop in the ledger whatever stopped the attempt (#2018).

    Only the capped client and the ledger itself wrote stopped_attempts, so a
    deadline or proxy stop left the attempt identity unmarked. Called after
    stop_explanation, so an existing ledger entry stays the authoritative
    cause (Ledger.stop_attempt never overwrites one). Never raises."""
    if receipt.get('reason_source') == 'ledger':
        return {}
    reason = str(receipt.get('reason') or receipt.get('error_type') or 'stopped')
    reason = reason if reason.startswith(CONTROLLER_PREFIX) else CONTROLLER_PREFIX + reason
    try:
        ledger.stop_attempt(billing_attempt, reason)
        state = json.loads(Path(ledger.path).read_bytes())
        held = ((state.get('stopped_attempts') or {}).get(billing_attempt) or {}).get('reason')
    except Exception as error:
        return {'ledger_stop_record_note': f'could not record the stop in the ledger: {type(error).__name__}'}
    if held == reason:
        return {'ledger_stop_recorded': reason}
    # Ledger.stop_attempt keeps the first entry; say what it holds instead.
    return {'ledger_stop_record_note': f'the ledger already held a stop entry: {held}'}


def stop_explanation(exc, ledger_path, billing_attempt, proxy_failure):
    """Why a native attempt stopped, from the strongest source available.

    The v10q CHORUS attempt stopped on a ledger refusal, but the receipt
    recorded only `error_type: PermissionError` with no reason: the proxy
    keeps the class name of a non-BudgetStop exception and the controller
    copied a reason only from a BudgetStop it raised itself (#1914). The
    ledger's own stop entry for this attempt is the authoritative cause
    whenever it exists; the proxy's recorded failure and the exception's
    BudgetStop message follow. Never raises: a diagnostic that fails must
    not displace the stop it explains (#1925), so a malformed or unreadable
    ledger is reported as such and the other sources still apply.
    """
    out = {}
    entry = None
    try:
        state = json.loads(Path(ledger_path).read_bytes()) if Path(ledger_path).exists() else {}
        stops = state.get('stopped_attempts') if isinstance(state, dict) else None
        entry = stops.get(billing_attempt) if isinstance(stops, dict) else None
        if stops is not None and not isinstance(stops, dict):
            out['ledger_stop_note'] = 'stopped_attempts is not a mapping'
    except Exception as read_error:
        out['ledger_stop_note'] = f'ledger unreadable: {type(read_error).__name__}'
    entry_reason = entry.get('reason') if isinstance(entry, dict) else None
    if isinstance(entry_reason, str) and entry_reason.startswith(CONTROLLER_PREFIX):
        # The controller recorded its own stop before closing admission (#2023).
        out['reason'] = entry_reason[len(CONTROLLER_PREFIX):]; out['reason_source'] = 'controller'; out['ledger_stop'] = entry
    elif (isinstance(entry_reason, str) and entry_reason == ADMISSION_CLOSED
          and isinstance(exc, BudgetStop) and str(exc) != ADMISSION_CLOSED and proxy_failure in (None, ADMISSION_CLOSED)):
        # A handler met the admission the controller had already closed: the
        # entry is a consequence of the controller's stop, not its cause.
        out['reason'] = str(exc); out['reason_source'] = 'controller'; out['ledger_stop'] = entry
        out['ledger_stop_note'] = 'the ledger entry records a request refused after the controller closed admission'
    elif isinstance(entry_reason, str) and entry_reason:
        out['reason'] = entry_reason; out['reason_source'] = 'ledger'; out['ledger_stop'] = entry
    elif isinstance(exc, BudgetStop):
        # The controller re-raises the proxy's recorded failure as a
        # BudgetStop; its source is the proxy (#2038).
        out['reason'] = str(exc)
        out['reason_source'] = 'proxy' if isinstance(proxy_failure, str) and proxy_failure and str(exc) == proxy_failure else 'controller'
    elif isinstance(proxy_failure, str) and proxy_failure:
        out['reason'] = proxy_failure; out['reason_source'] = 'proxy'
    else:
        # An exception nothing else explains still has a named stop (#2038).
        # Only its type is recorded; the traceback is kept beside the receipt.
        out['reason'] = f'unexpected {type(exc).__name__}'; out['reason_source'] = 'controller'
    if proxy_failure is not None:
        out['proxy_failure'] = proxy_failure
    return out


def observation_problems(observed):
    """What in a transcript observation refuses completion (#1930): a
    malformed measurement-bearing event means the coverage and totals are
    not evidence, whatever the current-file checks say."""
    if not isinstance(observed, dict):
        return ['transcript observation unavailable']
    problems = []
    if observed.get('malformed_message_events'):
        problems.append(f"transcript carries {observed['malformed_message_events']} malformed measurement events")
    if observed.get('overlapping_evidence'):
        problems.append(f"transcript carries {observed['overlapping_evidence']} overlapping evidence events (#1972)")
    if not observed.get('usage_from_terminal_result'):
        # The native runtime's stream-json ends in a result carrying usage;
        # an attempt whose transcript finalizes nothing is not complete (#2002).
        problems.append('transcript carries no terminal result with complete usage')
    return problems


def retain_traceback(attempt, exc):
    """Append the controller traceback under the attempt; never raise."""
    try:
        with (attempt / 'controller_traceback.txt').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'at': now(), 'error_type': type(exc).__name__}) + '\n' + traceback.format_exc() + '\n')
    except Exception:
        pass


def native_evidence_check(spec):
    """Recheck the exact originals using the generation's selected protocol."""
    from data_sheets_schema.evidence_assertions import check_files, protocol_for_renderer
    evidence_dir = spec.metadata_dir / 'evidence'
    return check_files(audit=evidence_dir/'audit.json', bundle=spec.bundle,
        manifest=spec.chunk_manifest, report=spec.report_path,
        artifacts={'original_full':evidence_dir/'original_full.yaml',
                   'original_core':evidence_dir/'original_core.yaml',
                   'final_full':spec.full_path,'final_core':spec.core_path},
        protocol_version=protocol_for_renderer(spec.render_version))


def terminate_group(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # Also remove descendants if the parent exited before them.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=2)


#: What an in-flight handler raises when the controller closed admission:
#: a consequence of a controller stop, never its cause (#2023).
ADMISSION_CLOSED = 'native admission is closed'
CONTROLLER_PREFIX = 'controller: '


def record_then_close(proxy, record_stop, reason):
    """Record the controller's stop and close admission as one step (#2023,
    #2029). Handlers write the ledger only under proxy.state, and the ledger's
    file lock does not wait, so the record takes that same (reentrant) lock:
    it neither collides with a handler's write nor lets a handler refused at
    the closed admission write the first stop entry. Never raises."""
    from contextlib import nullcontext
    guard = getattr(proxy, 'state', None) or nullcontext()
    with guard:
        if record_stop is not None:
            try:
                record_stop(reason)
            except Exception:
                pass
        proxy.close_admission()


def execute_child(argv, *, proxy, instruction, attempt, cwd, env, deadline_seconds, verify_launch, record_stop=None):
    process = None
    deadline = time.monotonic() + deadline_seconds
    try:
        with Path(instruction).open('r') as incoming, (attempt/'transcript.jsonl').open('x') as out, (attempt/'stderr.txt').open('x') as err:
            verify_launch()  # Bind the executable immediately before Popen.
            process = subprocess.Popen(argv, stdin=incoming, text=True, cwd=cwd,
                env=env, stdout=out, stderr=err, start_new_session=True)
            while process.poll() is None:
                if proxy.failed.is_set():
                    raise BudgetStop(proxy.failure)
                if time.monotonic() >= deadline:
                    raise BudgetStop('native attempt deadline elapsed; retain all incomplete charge reservations')
                time.sleep(0.05)
        if proxy.failed.is_set():
            raise BudgetStop(proxy.failure)
        return process.returncode
    except BaseException as exc:
        # Record every controller-originated failure before shutdown (#2042). An
        # in-flight counter can otherwise write "admission is closed" first
        # and hide an interrupt or unexpected exception behind that symptom.
        # A proxy failure already has its own cause; preserve it unchanged.
        failed = getattr(proxy, 'failed', None)
        if failed is None or not failed.is_set():
            reason = str(exc) if isinstance(exc, BudgetStop) else f'unexpected {type(exc).__name__}'
            record_then_close(proxy, record_stop, reason)
        raise
    finally:
        # This runs INSIDE proxy.running(), before server/pool cleanup.
        proxy.close_admission()
        terminate_group(process)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--job',required=True)
    args=parser.parse_args()
    overlay=json.loads(args.overlay.read_bytes())
    base_path=Path(overlay['registration']);base=json.loads(base_path.read_bytes())
    here=base_path.parent;registration_sha=sha(base_path);overlay_sha=sha(args.overlay)
    review=json.loads(args.review.read_bytes())
    if review.get('verdict')!='approve' or review.get('ci_conclusion')!='success' or review.get('overlay_sha256')!=overlay_sha or args.job not in review.get('allowed_jobs',[]):
        raise BudgetStop('this native execution overlay and job need independent approval and CI')
    if overlay.get('registration_sha256')!=registration_sha:
        raise BudgetStop('native overlay refers to another source/instrument registration')
    if args.job not in overlay['allowed_jobs']:
        raise BudgetStop('native job is outside this overlay')
    def verify_all():
        verify(base,base_path,registration_sha)
        if sha(args.overlay)!=overlay_sha:
            raise BudgetStop('native execution overlay changed')
        if any(not Path(p).is_file() or sha(p)!=h for p,h in overlay['pinned_files'].items()):
            raise BudgetStop('native controller or runtime pin changed')
    verify_all();verify_history(base)
    job=next(j for j in base['generation']['jobs'] if j['id']==args.job)
    if not job['canary'] or job['execution_arm']!='agentic':
        raise BudgetStop('this controller only launches registered agentic generation canaries')
    order=base['generation']['canary_order']
    for previous in order[:order.index(args.job)]:
        accepted=json.loads((here/'acceptances'/f'{previous}.json').read_bytes())
        if accepted.get('verdict')!='accept' or accepted.get('registration_sha256')!=registration_sha or not accepted.get('artifacts') or any(not Path(p).is_file() or sha(p)!=h for p,h in accepted['artifacts'].items()):
            raise BudgetStop('earlier canary lacks acceptance of unchanged original artifacts')
    if any(Path(p).exists() for p in job['output_directories']):
        raise BudgetStop('native canary output already exists; never overwrite or resume')
    spec=spec_for(job)
    if spec.render_spec()!=job['render_spec'] or spec.input_identity()!=job['input_identity']:
        raise BudgetStop('native generation instruction or input identity changed')
    if spec.render_version >= 9 and overlay['per_job_environment'][job['id']].get('D4D_LAUNCH_INSTRUCTION') != job['instruction']:
        raise BudgetStop('native provenance must read the exact registered launch instruction')
    try:
        command_policy=validated_command_policy(overlay,base,job)
    except (KeyError, OSError, ValueError, TypeError, SyntaxError) as error:
        raise BudgetStop(f'native command policy is invalid: {error}') from error
    key=os.environ.get('CBORG_API_KEY')
    if not key: raise BudgetStop('CBORG_API_KEY is required')
    executable=verified_executable(overlay)
    if subprocess.check_output([executable,'--version'],text=True).strip()!=base['claude_version']:
        raise BudgetStop('native runtime version changed')
    attempt=here/'attempts'/args.job;attempt.mkdir(parents=True,exist_ok=False)
    config=attempt/'cli_config';config.mkdir(mode=0o700)
    ledger=open_ledger(base,registration_sha)
    billing_attempt=attempt_identity(registration_sha,job['id'])
    proxy=NativeProxy(sdk=cborg_client(base,key,max_retries=0),
          ledger=ledger,attempt=billing_attempt,evidence=attempt/'requests',model=base['model']['model'],
          prices=base['budget']['prices_per_token'],verify=verify_all,provider_key=key,base_url=base['provider_base_url'],
          request_headers=provider_context_headers(base))
    # Explicitly whitelist non-credential environment fields. The child gets
    # only the local transport token; provider credentials stay in the parent.
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','SHELL','TMPDIR','LANG','LC_ALL','TERM'}}
    env.update(overlay['environment'])
    env.update(overlay['per_job_environment'][job['id']])
    env.update(CLAUDE_CONFIG_DIR=str(config),ANTHROPIC_API_KEY=proxy.token,
               PYTHONPATH=str(Path(base['repository'])/'src'),VIRTUAL_ENV=sys.prefix)
    system_prompt=Path(overlay['system_prompt']).read_text()+command_guidance(command_policy)
    argv=[executable,*overlay['cli_flags'],'--model',base['model']['model'],'--name',job['id'],
          '--max-budget-usd',str(ledger.limit_for_attempt(billing_attempt)),
          *permission_arguments(command_policy),
          '--system-prompt',system_prompt]
    receipt={'job':job['id'],'registration_sha256':registration_sha,'overlay_sha256':overlay_sha,
             'provider_context':provider_context_evidence(base),
             'review_sha256':sha(args.review),'started_at':now(),'status':'incomplete',
             'launch_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
             'provider':base['provider_base_url'],'model':base['model']['model'],
             'instruction_sha256':sha(job['instruction']),'native_system_sha256':sha(overlay['system_prompt']),
             'native_effective_system_sha256':hashlib.sha256(system_prompt.encode('utf-8')).hexdigest()}
    write_new(attempt/'started.json',receipt)
    def classify(denials):
        return classify_denials(denials, instruction_text=Path(job['instruction']).read_text(encoding='utf-8'),
            python=base.get('python'), repository=base['repository'],
            output_directories=job['output_directories'], readable_inputs=registered_reads(job), command_policy=command_policy)
    try:
        with proxy.running() as url:
            env['ANTHROPIC_BASE_URL']=url
            receipt['exit_code']=execute_child(argv,proxy=proxy,instruction=job['instruction'],attempt=attempt,
                cwd=base['repository'],env=env,deadline_seconds=base['generation']['agentic_attempt_deadline_seconds'],
                verify_launch=lambda: verified_executable(overlay),
                record_stop=lambda reason: receipt.update(
                    pre_close_ledger_stop=record_controller_stop(ledger, billing_attempt, {'reason': reason})))
        if proxy.failed.is_set() or proxy.unfinished_handlers:
            raise BudgetStop(proxy.failure or 'native handlers did not finish before evidence freeze')
        # JSONL separates records with physical newlines (#2043). Unicode NEL/line/
        # paragraph separators can appear literally inside valid JSON strings.
        with (attempt/'transcript.jsonl').open(encoding='utf-8') as transcript:
            events=[json.loads(line) for line in transcript if line.strip()]
        initializers=[e for e in events if e.get('type')=='system' and e.get('subtype')=='init']
        finals=[e for e in events if e.get('type')=='result']
        if len(initializers)!=1 or len(finals)!=1:
            raise BudgetStop('native runtime initialization or terminal result is missing or ambiguous')
        init,terminal=initializers[0],finals[0]
        if init.get('model')!=base['model']['model'] or init.get('apiKeySource')!='ANTHROPIC_API_KEY' or init.get('claude_code_version')!=base['claude_version'].split()[0] or set(init.get('tools',[]))!={'Read','Write','Bash'}:
            raise BudgetStop('native runtime initialization differs from registration')
        # Every denial is listed and classified; only a denied prescribed
        # command (or an unclassifiable record) disqualifies, and it does so
        # after every other check has run (#2026).
        receipt['permission_denials']=classify(terminal.get('permission_denials'))
        receipt['command_history']=command_history(events, command_policy, receipt['permission_denials'])
        if receipt['exit_code'] or terminal.get('is_error') or terminal.get('terminal_reason')!='completed' or terminal.get('stop_reason')!='end_turn':
            raise BudgetStop('native attempt failed or stopped before completion')
        if set(terminal.get('modelUsage',{}))!={base['model']['model']}:
            raise BudgetStop('native terminal model accounting differs from registration')
        observed=terminal['modelUsage'][base['model']['model']]
        expected_limits=overlay['native_limits_observed_offline']
        if observed.get('contextWindow')!=expected_limits['context_window'] or observed.get('maxOutputTokens')!=expected_limits['max_output_tokens']:
            raise BudgetStop('native runtime limits differ from the registered observation')
        state=json.loads(ledger.path.read_bytes())
        rows=[r for r in state['requests'] if r['attempt']==billing_attempt]
        if not rows or any(r['status']!='settled' for r in rows):
            raise BudgetStop('native attempt has missing or unresolved request accounting')
        if not all(Path(p).is_file() for p in job['outputs'].values()):
            raise BudgetStop('native generation did not produce every registered artifact')
        from data_sheets_schema import api_runner, agentic_observed
        problems=api_runner.validate_outputs(spec)
        pair=api_runner.pair_consistency(spec)
        receipt_check=check_canary_receipts(spec,job['input_identity'])
        receipt['receipt_acceptance']=receipt_check
        if not receipt_check['passed']:
            problems=list(problems)+['coverage receipt acceptance failed']
        if spec.render_version >= 9:
            try:
                evidence = native_evidence_check(spec)
                evidence_problem = None if evidence['checked'] and not evidence['findings'] else 'explicit evidence assertions failed'
            except Exception as error:
                # Missing or malformed evidence inputs are the run's defect,
                # checked like any other, not a controller stop (#2038); the
                # prescribed evidence CLI reports them the same way.
                evidence = {'checked': False, 'error_type': type(error).__name__}
                evidence_problem = f'explicit evidence assertions could not be checked ({type(error).__name__})'
            receipt['evidence_assertions'] = evidence
            if evidence_problem:
                problems = list(problems) + [evidence_problem]
        observed=agentic_observed.observe([attempt/'transcript.jsonl'],Path(job['bundle']))
        problems=(list(problems)+observation_problems(observed)+denial_problems(receipt['permission_denials'])
                  +receipt['command_history']['problems'])
        receipt.update(validation_problems=problems,pair_consistency=pair,
                       native_observed=observed,
                       cli_reported_cost_usd=terminal.get('total_cost_usd'),cli_model_usage=terminal.get('modelUsage'),
                       status='validation_failed' if problems or not pair or not pair.get('ran') or not pair.get('consistent') else 'completed_pending_independent_review')
        verify_all();verify_history(base)
    except BaseException as exc:
        # BaseException: an interrupted controller records its stop like any
        # other (#2018, #2038) and exits non-zero.
        receipt.update(status='stopped',error_type=type(exc).__name__)
        receipt.update(stop_explanation(exc, ledger.path, billing_attempt, getattr(proxy, 'failure', None)))
        receipt.update(transcript_terminal_state(attempt/'transcript.jsonl'))
        if 'permission_denials' in receipt:
            # Classified before the stop: name what would disqualify (#2037).
            receipt['disqualifying_denials'] = denial_problems(receipt['permission_denials'])
        else:
            receipt.update(stopped_denials(attempt/'transcript.jsonl', classify))
        # The traceback names controller code paths only; provider exception
        # strings are never copied into the receipt.
        retain_traceback(attempt, exc)
        receipt.update(record_controller_stop(ledger, billing_attempt, receipt))
    finally:
        try:
            state=json.loads(ledger.path.read_bytes()) if ledger.path.exists() else {'requests':[]}
            admitted=[row for row in state.get('requests',[]) if isinstance(row,dict) and row.get('attempt')==billing_attempt]
        except Exception as read_error:
            admitted=None; receipt['ledger_read_note']=f'ledger unreadable at freeze: {type(read_error).__name__}'
        receipt.update(finished_at=now(),model_requests_admitted=None if admitted is None else len(admitted),
            unfinished_handlers_at_freeze=proxy.unfinished_handlers,
            artifacts={str(p):sha(p) for folder in job['output_directories'] for p in sorted(Path(folder).rglob('*')) if p.is_file()})
        write_new(attempt/'result.json',receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k not in {'artifacts','validation_problems','pair_consistency','native_observed','cli_model_usage'}},indent=2))
    return 0 if receipt['status']=='completed_pending_independent_review' else 1


if __name__=='__main__':
    raise SystemExit(main())
