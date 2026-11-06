"""D4D Command-Line Interface.

Unified CLI for D4D data sheets schema operations.

Usage:
    d4d --help
    d4d download sources --project AI_READI
    d4d evaluate presence --project AI_READI --method gpt5
    d4d utils status --quick
    d4d validate datasheet.yaml --schema core
"""

# Diagnostic-only U0 second pair: identical source-bound observer in both arms.
import sys as _u0_second_sys
if _u0_second_sys.argv[1:3] == ["provenance", "record"]:
    import hashlib as _u0_second_hashlib
    import runpy as _u0_second_runpy
    from pathlib import Path as _u0_second_Path
    _u0_second_root = _u0_second_Path(__file__).resolve().parents[3]
    for _u0_second_rel, _u0_second_sha in {'scripts/adhoc/native_recorder_observer_20261026.py': 'cc7ba1ae1daf8492255aac34fb306d8a613823f768e9b7f6950402c0c03ab284', 'scripts/adhoc/native_recorder_thread_cpu_20261106.py': '60effc35d535df4c93be4a6e2b2c5c98a71da2251a571d887292870dfbfa9547', 'scripts/adhoc/native_u0_source_closure_20261106.py': 'd9e95e2e8c4d178e4f6bd3093a65695a4568a2bcc230d4cd24b21262ca4e396e', 'scripts/adhoc/native_recorder_second_cpu_20261106.py': '1f2fd38ca91af01e3c1773b5ff019c1f0871f896d5a51fcda21357e3f952bfd0', 'scripts/adhoc/native_recorder_second_cpu_20261106.config.json': '993c9d7ae15001e41bc9f2f89d1770b7a916f66a2f9ed88d1c41b9be179e34db'}.items():
        if _u0_second_hashlib.sha256((_u0_second_root / _u0_second_rel).read_bytes()).hexdigest() != _u0_second_sha:
            raise RuntimeError("U0 second pair helper hash differs")
    _u0_second_runpy.run_path(str(_u0_second_root / "scripts/adhoc/native_recorder_second_cpu_20261106.py"))["install_from_config"](_u0_second_root)


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
