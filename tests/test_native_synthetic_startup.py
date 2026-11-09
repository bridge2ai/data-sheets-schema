"""U3-J2 ordinary-Python startup canary, 2026-11-09; no native/provider use.

The one child runs a tiny test fixture with the required -P shebang, not the
generation peer. Its artifacts establish import isolation before Python code
could call a runtime guard. Run through the network-denied offline harness.
"""
import json
from pathlib import Path
import subprocess
import sys


def test_safe_path_shebang_excludes_peer_directory_before_first_import(tmp_path):
    root = tmp_path.resolve()
    home = root / 'synthetic-home'
    home.mkdir()
    sentinel = root / 'shadow-imported.txt'
    shadow = root / 'json.py'
    shadow.write_text(
        "with open('shadow-imported.txt', 'x', encoding='utf-8') as stream:\n"
        "    stream.write('untrusted sibling executed')\n"
        "raise RuntimeError('the peer directory entered import discovery')\n")
    script = root / 'ordinary-python-startup'
    script.write_text('#!' + sys.executable + ' -P\n'
        'import json\n'
        'import sys\n'
        "with open('startup-result.json', 'x', encoding='utf-8') as stream:\n"
        "    json.dump({'safe_path': sys.flags.safe_path, 'json_origin': json.__file__}, stream)\n")
    script.chmod(0o700)
    environment = {'PATH': '/usr/bin:/bin', 'HOME': str(home),
                   'LANG': 'C', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    completed = subprocess.run([str(script)], cwd=root, env=environment,
        capture_output=True, text=True, timeout=15, check=False)
    assert completed.returncode == 0, completed.stderr
    output = root / 'startup-result.json'
    assert output.is_file() and output.stat().st_size > 0
    observed = json.loads(output.read_bytes())
    assert observed == {'safe_path': True, 'json_origin': json.__file__}
    assert Path(observed['json_origin']).resolve() != shadow
    assert not sentinel.exists()
    assert list(home.iterdir()) == []
