"""Issue 6214, 2026-11-15: resolve local review R1/R2 in source and tests."""
from pathlib import Path
p = Path('src/data_sheets_schema/native_shared_callback_orchestration.py')
s = p.read_text().replace('_POISONED_STACKS = []', "# sys is process-rooted even when a verified loader restores module bindings.\n_POISONED_STACKS = sys.__dict__.setdefault('_d4d_poisoned_callback_stacks', [])")
s = s.replace('    stack = ExitStack()\n    try:\n        yield stack', '    if isinstance(lock, _CallbackLock):\n        lock.check()\n    stack = ExitStack()\n    try:\n        yield stack', 1)
p.write_text(s)
p = Path('tests/test_native_shared_callback_teardown.py')
s = p.read_text().replace('import gc\n', 'import gc\nimport sys\n')
s = s.replace('        assert stack in preload._POISONED_STACKS', "        assert stack in preload._POISONED_STACKS\n        assert stack in sys.__dict__['_d4d_poisoned_callback_stacks']")
s = s.replace('            with preload._locked_stack(lock):\n                pass', "            with preload._locked_stack(lock):\n                pytest.fail('poisoned scope body entered')")
p.write_text(s)
p = Path('tests/test_native_shared_callback_preloading.py')
s = p.read_text().replace('        def __exit__(self, *exc):\n            lock.release()\n', '')
p.write_text(s)
p = Path('tests/test_native_shared_callback_teardown.py')
s = p.read_text() + '''

def test_poisoned_classifier_refuses_both_entries_before_calling_code():
    lock = preload._CallbackLock()
    lock.poisoned = True
    def forbidden(*args, **kwargs):
        pytest.fail('poisoned classifier called retained code')
    classifier = preload.Classifier(forbidden, forbidden, object(), forbidden, forbidden, lock)
    with pytest.raises(ValueError, match='poisoned'):
        classifier.classify('pwd', 'python', set(), {})
    with pytest.raises(ValueError, match='poisoned'):
        classifier.readonly('pwd', {})
'''
p.write_text(s)
