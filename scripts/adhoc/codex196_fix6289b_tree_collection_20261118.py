"""Parse the saved pytest7 collection tree into exact node IDs, 2026-11-18.
Inputs: verbose full-collection log. Output: in-memory ordered node IDs for
F3 multiplicity proof. No collection execution, code-worktree writes, or I/O
other than reading the supplied log.
"""
import re


def parse_tree(path):
    stack, nodes = [], []
    seen_types = set()
    for raw in path.read_text().splitlines():
        match = re.fullmatch(r'( *)<(Package|Module|Class|UnitTestCase|Function|TestCaseFunction) (.*)>', raw)
        if not match:
            continue
        indent, kind, name = match.groups()
        depth = len(indent)
        seen_types.add(kind)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if kind in ('Function', 'TestCaseFunction'):
            files = [value for _, category, value in stack if category in ('Package', 'Module')]
            classes = [value for _, category, value in stack if category in ('Class', 'UnitTestCase')]
            if files and files[0] != 'tests':
                files.insert(0, 'tests')
            if not files or not files[-1].endswith('.py'):
                raise ValueError('function lacks a complete tests module path: ' + repr((raw, stack)))
            nodes.append('::'.join(['/'.join(files), *classes, name]))
        else:
            stack.append((depth, kind, name))
    header = re.search(r'^collected (\d+) items / (\d+) errors$', path.read_text(), re.M)
    if header is None or len(nodes) != int(header.group(1)):
        raise ValueError('parsed tree item count differs from pytest header')
    if seen_types != {'Package', 'Module', 'Class', 'UnitTestCase', 'Function', 'TestCaseFunction'}:
        raise ValueError('unexpected collection object inventory')
    return nodes
