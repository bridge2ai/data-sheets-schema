"""D4D Command-Line Interface.

Unified CLI for D4D data sheets schema operations.

Usage:
    d4d --help
    d4d download sources --project AI_READI
    d4d evaluate presence --project AI_READI --method gpt5
    d4d utils status --quick
    d4d validate datasheet.yaml --schema core
"""

# U0 diagnostic-only dependency binding; no production authority exception.
import sys as _u0_profile_sys
if _u0_profile_sys.argv[1:3] == ["provenance", "record"]:
    from pathlib import Path as _u0_profile_Path
    import hashlib as _u0_profile_hashlib
    _u0_profile_root = _u0_profile_Path(__file__).resolve().parents[3]
    for _u0_profile_rel, _u0_profile_sha in {'scripts/adhoc/native_recorder_observer_20261026.py': 'cc7ba1ae1daf8492255aac34fb306d8a613823f768e9b7f6950402c0c03ab284', 'scripts/adhoc/native_recorder_cpu_profile_20261106.py': 'ca3381088b40f3635821012eb4c08c1d86121150ed6e77b87eec70f9218325c7', 'scripts/adhoc/native_recorder_cpu_profile_20261106.config.json': '016ab51208b410e6ec324240bfdb945678a4342455209be8994cfb0548f33f6b'}.items():
        if _u0_profile_hashlib.sha256((_u0_profile_root / _u0_profile_rel).read_bytes()).hexdigest() != _u0_profile_sha:
            raise RuntimeError("U0 diagnostic tooling hash differs")
# Diagnostic-only CPU observer; never install in baseline sources.
import sys as _recorder_cpu_sys
if _recorder_cpu_sys.argv[1:3] == ["provenance", "record"]:
    import runpy as _recorder_cpu_runpy
    from pathlib import Path as _recorder_cpu_Path
    _recorder_cpu_root = _recorder_cpu_Path(__file__).resolve().parents[3]
    _recorder_cpu_runpy.run_path(str(
        _recorder_cpu_root / "scripts/adhoc/native_recorder_cpu_profile_20261106.py"
    ))["install_from_config"](_recorder_cpu_root)


import click

@click.group()
@click.version_option()
@click.option("--manifest", default=None, envvar="D4D_MANIFEST", is_eager=True,
              help="the source manifest that is the project registry for every command "
                   "that names a --project and has no --manifest of its own (#623); "
                   "default data/preprocessed/source_manifest.yaml")
def cli(manifest):
    """D4D command-line interface for dataset documentation."""
    pass

# Import and register subcommands
from . import download, evaluate, utils, rocrate, schema, render, healthsheet, runs, provenance, api, enrich, prompt, derive, bundle, receipts, review, agents, validate

cli.add_command(download.download)
cli.add_command(evaluate.evaluate)
cli.add_command(utils.utils)
cli.add_command(rocrate.rocrate)
cli.add_command(healthsheet.healthsheet)
cli.add_command(runs.runs)
cli.add_command(enrich.enrich)
cli.add_command(provenance.provenance)
cli.add_command(schema.schema)
cli.add_command(render.render)
cli.add_command(api.api)
cli.add_command(prompt.prompt)
cli.add_command(derive.derive)
cli.add_command(bundle.bundle)
cli.add_command(receipts.receipts)
cli.add_command(review.review)
cli.add_command(agents.agents)
cli.add_command(validate.validate)

if __name__ == "__main__":
    cli()
