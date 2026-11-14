#!/usr/bin/env python3
"""Check the repaired offline CI sandbox, issues 6201/6202, 2026-11-13.
Input: the integration runner's exact profile. Output: retained profile and
JSON proof that loopback works while Unix-domain listening is denied.
Every operation stays on this host. No external address is attempted.
"""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys


def load_runner():
    path = Path(__file__).with_name('run_h2_integration_20261113.py')
    spec = importlib.util.spec_from_file_location('integration_runner', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner, path


def worker():
    runner, _ = load_runner()
    witness = runner.network_witness(Path.cwd(), allow_loopback=True)
    assert witness['network_operation_denied']
    with socket.socket() as server, socket.socket() as client:
        server.settimeout(5)
        client.settimeout(5)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        client.connect(server.getsockname())
        client.sendall(b'offline')
        connection, peer = server.accept()
        with connection:
            connection.settimeout(5)
            assert connection.recv(7) == b'offline'
        assert peer[0] == '127.0.0.1'
    print(json.dumps({'loopback_exchange': True, 'unix_domain_listen_denied': True,
                      'external_address_attempted': False}))


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        runner, path = load_runner()
        out = runner.SCRATCH_BASE / 'loopback-preflight-local-v2'
        out.mkdir(exist_ok=False)
        profile = out / 'network-denied.sb'
        profile.write_text(runner.sandbox_profile(allow_loopback=True))
        command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable,
                   '-S', '-P', '-B', str(Path(__file__).resolve()), '--worker']
        result = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=15)
        runner.save(out / 'result.json', {'command': command, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr,
            'runner_sha256': runner.digest(path), 'profile_sha256': runner.digest(profile)})
        assert result.returncode == 0, result.stderr
        print(result.stdout.strip())
