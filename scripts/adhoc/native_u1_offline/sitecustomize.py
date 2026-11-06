"""U1 #4354 offline test guard, 2026-11-06; no network or native runtime."""
import os
import sys

def guard(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
        raise RuntimeError('U1 offline: network denied')
    if event in ('subprocess.Popen', 'os.exec', 'os.posix_spawn'):
        executable = os.path.basename(os.fsdecode(args[0]))
        if executable in ('claude', 'codex', 'gemini', 'curl', 'wget', 'gh'):
            raise RuntimeError('U1 offline: native/network executable denied')
sys.addaudithook(guard)
