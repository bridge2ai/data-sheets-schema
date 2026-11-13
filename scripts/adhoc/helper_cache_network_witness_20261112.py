# Test-only startup audit for issue 5966, 2026-11-12; NETWORK_DIRECTORY is injected
# by the isolated runner. Records every Python socket/DNS attempt; the independent
# OS sandbox denies network, including non-Python attempts. No code is replaced.
import os
import sys
import json
import time
from pathlib import Path
_destination = Path(NETWORK_DIRECTORY) / (str(os.getpid()) + '.jsonl')
def _write(row):
    with _destination.open('a') as stream:
        stream.write(json.dumps(row,sort_keys=True)+'\n')
_write({'event':'python_start','pid':os.getpid(),'argv':sys.argv,'wall_ns':time.time_ns()})
def _network_audit(event,args):
    if event in ('socket.connect','socket.bind','socket.sendto','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr'):
        _write({'event':event,'pid':os.getpid(),'argv':sys.argv,'arguments':repr(args),'wall_ns':time.time_ns()})
sys.addaudithook(_network_audit)
