"""D68-D70/#5212 review item 7: preserve pytest stdout, 2026-10-30.

Inputs: subprocess argv, checkout, and pytest basetemp. Output: pytest.log
inside basetemp, never a live log elsewhere in the checkout being tested.
"""
import signal
import subprocess


def run_logged(command, base, *, cwd):
    """Buffer startup output until pytest has initialized its scratch tree."""
    pending = bytearray()
    stream = None
    with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        def drain():
            nonlocal stream
            while chunk := process.stdout.read1(65536):
                if stream is None and (base / "offline-bin/git").is_file():
                    stream = (base / "pytest.log").open("xb")
                    stream.write(pending)
                    pending.clear()
                if stream is None:
                    pending.extend(chunk)
                else:
                    stream.write(chunk)
                    stream.flush()
        try:
            drain()
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
            drain()
        finally:
            if stream is not None:
                stream.close()
        code = process.wait()
    if stream is None:
        base.mkdir(parents=True, exist_ok=True)
        (base / "pytest.log").write_bytes(pending)
    assert (base / "pytest.log").stat().st_size
    return code
