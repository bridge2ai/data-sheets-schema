"""Utilities command group for D4D CLI.

Commands for utility operations like status checks.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.registry import load_registry, project_choice
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

@click.group()
def utils():
    """Utility commands."""
    pass

@utils.command()
@click.option('--quick', is_flag=True, help='Show compact overview')
@click.option('--manifest', type=click.Path(), default='data/preprocessed/source_manifest.yaml',
              show_default=True, help='the source manifest whose projects are listed (#637)')
@click.option('--data-dir', type=click.Path(path_type=Path), default=Path('data'),
              show_default=True, help='Pipeline data root containing the generated method directories')
def status(quick, manifest, data_dir):
    """Show data pipeline status and file counts."""
    registry = load_registry(manifest)
    if quick:
        _show_compact_status(registry, data_dir)
    else:
        _show_detailed_status(registry, data_dir)

@utils.command('validate-preprocessing')
@click.option('--raw-dir', type=click.Path(), default='data/raw',
              help='Raw data directory')
@click.option('--preprocessed-dir', type=click.Path(),
              default='data/preprocessed/individual',
              help='Preprocessed data directory')
@click.option('--manifest', type=click.Path(), default='data/preprocessed/source_manifest.yaml',
              show_default=True, is_eager=True, help='the registry for --project')
@click.option('--project', callback=project_choice,
              help='Validate specific project only')
def validate_preprocessing(raw_dir, preprocessed_dir, manifest, project):
    """Validate preprocessing quality (check for empty/stub files)."""
    require_repo_context("d4d utils validate-preprocessing")

    setup_repo_imports()
    from src.download.validate_preprocessing_quality import main as validate_main

    # Set up args for the validation script
    old_argv = sys.argv
    sys.argv = ['validate_preprocessing_quality.py',
                '--raw-dir', raw_dir,
                '--preprocessed-dir', preprocessed_dir,
                '--manifest', manifest]
    # The registry's projects, not the validator's own four (#1367 review,
    # should-fix 1); a project whose files are another project's directory
    # has nothing of its own to validate.
    reg = load_registry(manifest)
    names = [project] if project else [p for p in reg.projects()
                                      if reg.shared_source_project(p, Path(preprocessed_dir)) is None]
    if names:
        sys.argv.append('--projects'); sys.argv.extend(names)

    try:
        validate_main()
    finally:
        sys.argv = old_argv

def _source_directories(registry, data_dir, processed=False):
    for project in registry.projects():
        if processed:
            path = registry.source_dir(project) or data_dir / 'preprocessed/individual' / project
        else:
            owner = registry.shared_source_project(project, data_dir / 'preprocessed/individual')
            path = (registry.raw_dir(project) or (registry.raw_dir(owner) if owner else None)
                    or data_dir / 'raw' / (owner or project))
        yield project, path


def _show_compact_status(registry, data_dir):
    """Count the selected dataset sources and the selected output tree."""
    click.echo("📊 D4D Pipeline Status (Compact)")
    click.echo("=" * 60)
    sections = [
        ("Raw Downloads", {p for _, p in _source_directories(registry, data_dir)}),
        ("Preprocessed", {p for _, p in _source_directories(registry, data_dir, True)}),
        ("D4D Individual", {data_dir / 'd4d_individual'}),
        ("D4D Concatenated", {data_dir / 'd4d_concatenated'}),
    ]
    for name, roots in sections:
        paths = {p.resolve() for root in roots if root.is_dir() for p in root.rglob('*')}
        file_count = sum(p.is_file() for p in paths)
        dir_count = sum(p.is_dir() for p in paths)
        click.echo(f"  {name:20} {file_count:4} files, {dir_count:3} dirs")


def _show_detailed_status(registry, data_dir):
    click.echo("📊 D4D Pipeline Status (Detailed)")
    click.echo("=" * 60)
    for heading, processed in (("📁 Raw Downloads", False), ("🔄 Preprocessed", True)):
        click.echo(f"\n{heading}:")
        for project, directory in _source_directories(registry, data_dir, processed):
            count = sum(p.is_file() for p in directory.rglob('*')) if directory.is_dir() else None
            detail = f"{count:4} files" if count is not None else "⚠️  Not found"
            click.echo(f"  {project:12} {detail}  {directory}")
    for heading, relative in (("📄 D4D Individual", 'd4d_individual'),
                              ("📑 D4D Concatenated", 'd4d_concatenated')):
        click.echo(f"\n{heading}:")
        root = data_dir / relative
        methods = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        for directory in methods:
            count = sum(1 for p in directory.rglob('*.yaml') if p.is_file())
            click.echo(f"  {directory.name:20} {count:4} YAML files")
        if not methods:
            click.echo("  No method output directories")
