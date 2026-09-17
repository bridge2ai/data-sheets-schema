"""File-tool admission and provenance of the runtime's persisted tool output.

This checks declared file operations; it is not an OS filesystem sandbox.
Registered helpers still require argument and output review.
"""
import hashlib
from pathlib import Path
import re

from budgeted_cborg import BudgetStop


class FileAccess:
    def __init__(self, policy, config_root=None):
        paths = policy.get('readonly_lookups', {})
        self.root = Path(paths.get('repository', '.')).resolve()
        # Keep the frozen canonical paths, not a new resolution of an input
        # or output root which could now be a link to somewhere else.
        self.inputs = {Path(p) for p in paths.get('inputs', [])}
        self.outputs = [Path(p) for p in paths.get('output_directories', [])]
        self.config = Path(config_root).resolve() if config_root else None
        self.session = None
        self.persisted = {}

    def target(self, value):
        if not isinstance(value, str) or not value.strip() or '\0' in value:
            raise ValueError('missing or malformed file path')
        path = Path(value)
        return (path if path.is_absolute() else self.root / path).resolve()

    def matches(self, tool, original, callback):
        """The native runtime makes file paths absolute before the hook.

        Permit that spelling change only; offsets, limits and write contents
        still have to match the observed call exactly.
        """
        if tool == 'Bash':
            return original == callback
        left, right = dict(original), dict(callback)
        try:
            one, two = self.target(left.pop('file_path')), self.target(right.pop('file_path'))
        except (OSError, ValueError, RuntimeError, KeyError):
            return False
        return one == two and left == right

    def classify(self, tool, payload):
        try:
            target = self.target(payload.get('file_path'))
            if tool == 'Read' and target in self.inputs:
                return 'prescribed', 'a registered input the instruction reads'
            if any(folder in target.parents for folder in self.outputs):
                if target.exists() and (not target.is_file() or target.stat().st_nlink != 1):
                    return 'not_prescribed', 'an output target that is not a single-link regular file'
                if target in self.inputs:
                    return 'not_prescribed', 'a registered input cannot be overwritten'
                return 'prescribed', 'a file inside the registered output directories'
            if tool == 'Read' and str(target) in self.persisted:
                expected = self.persisted[str(target)]
                if self.fingerprint(target) != expected['file']:
                    raise BudgetStop('native persisted tool output changed before its read')
                return 'prescribed', 'an unchanged persisted result from this native session'
        except BudgetStop:
            raise
        except (OSError, ValueError, RuntimeError) as error:
            raise BudgetStop('native file target could not be resolved') from error
        return 'not_prescribed', 'a path outside the registered inputs and outputs'

    @staticmethod
    def fingerprint(path):
        if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
            raise BudgetStop('native persisted output is not a single-link regular file')
        raw = path.read_bytes()
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def observe(self, event, calls, decisions):
        """Trust native result metadata, never a filename mentioned by a source.

        Grant only a file below the current config/project/session tool-results
        directory, advertised by an admitted Bash result. Record its
        bytes now so the read and terminal audit can detect later changes.
        """
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            session = event.get('session_id')
            if (self.session is not None or event.get('cwd') != str(self.root) or
                not isinstance(session, str) or not re.fullmatch(r'[0-9a-f-]{36}', session)):
                raise BudgetStop('native file policy has ambiguous session identity')
            self.session = session
        metadata = event.get('tool_use_result')
        if not isinstance(metadata, dict) or 'persistedOutputPath' not in metadata:
            return None
        try:
            if event.get('type') != 'user' or self.config is None or self.session is None:
                raise ValueError('persisted result outside an initialized native session')
            if event.get('session_id') != self.session:
                raise ValueError('persisted result belongs to another session')
            blocks = event['message']['content']
            if not isinstance(blocks, list) or len(blocks) != 1:
                raise ValueError('ambiguous persisted result')
            block = blocks[0]
            identity = block['tool_use_id']
            if (block.get('type') != 'tool_result' or
                calls.get(identity, {}).get('name') != 'Bash' or
                decisions.get(identity) != 'prescribed'):
                raise ValueError('persisted result lacks a prescribed Bash call')
            raw_path = metadata['persistedOutputPath']
            path = Path(raw_path)
            project = re.sub(r'[^a-zA-Z0-9]', '-', str(self.root))
            directory = self.config / 'projects' / project / self.session / 'tool-results'
            if (not path.is_absolute() or path.parent != directory or path.resolve() != path or
                not re.fullmatch(r'[A-Za-z0-9_-]+\.txt', path.name)):
                raise ValueError('persisted result outside the current tool-results directory')
            content = block.get('content')
            if (not isinstance(content, str) or not content.startswith('<persisted-output>\n') or
                f'Full output saved to: {raw_path}\n' not in content):
                raise ValueError('native result metadata disagrees with its wrapper')
            fingerprint = self.fingerprint(path)
            size = metadata.get('persistedOutputSize')
            if type(size) is not int or size != fingerprint['bytes']:
                raise ValueError('persisted result size disagrees with native metadata')
            value = {'kind': 'persisted_output', 'tool_use_id': identity,
                     'path': str(path), 'file': fingerprint}
            if str(path) in self.persisted:
                raise ValueError('persisted result path was reused')
            self.persisted[str(path)] = value
            return value
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise BudgetStop('native persisted tool output has invalid provenance') from error
