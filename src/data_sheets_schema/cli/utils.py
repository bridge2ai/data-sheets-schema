"""Utilities command group for D4D CLI.

Commands for utility operations like status checks.
"""

import click
from pathlib import Path
from data_sheets_schema.constants import PROJECTS, METHODS

@click.group()
def utils():
    """Utility commands."""
    pass

@utils.command()
@click.option('--quick', is_flag=True, help='Show compact overview')
def status(quick):
    """Show data pipeline status and file counts."""
    from data_sheets_schema.constants import PROJECT_PATHS

    if quick:
        _show_compact_status()
    else:
        _show_detailed_status()

@utils.command('validate-preprocessing')
@click.option('--raw-dir', type=click.Path(exists=True), default='data/raw',
              help='Raw data directory')
@click.option('--preprocessed-dir', type=click.Path(exists=True),
              default='data/preprocessed/individual',
              help='Preprocessed data directory')
@click.option('--project', type=click.Choice(PROJECTS),
              help='Validate specific project only')
def validate_preprocessing(raw_dir, preprocessed_dir, project):
    """Validate preprocessing quality (check for empty/stub files)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from src.download.validate_preprocessing_quality import main as validate_main

    # Set up args for the validation script
    import sys
    old_argv = sys.argv
    sys.argv = ['validate_preprocessing_quality.py',
                '--raw-dir', raw_dir,
                '--preprocessed-dir', preprocessed_dir]
    if project:
        sys.argv.extend(['--project', project])

    try:
        validate_main()
    finally:
        sys.argv = old_argv

def _show_compact_status():
    """Show compact pipeline status."""
    data_dir = Path('data')

    click.echo("📊 D4D Pipeline Status (Compact)")
    click.echo("=" * 60)

    # Count files in key directories
    sections = [
        ("Raw Downloads", "raw"),
        ("Preprocessed", "preprocessed/individual"),
        ("D4D Individual", "d4d_individual"),
        ("D4D Concatenated", "d4d_concatenated"),
    ]

    for section_name, subdir in sections:
        section_path = data_dir / subdir
        if section_path.exists():
            file_count = sum(1 for _ in section_path.rglob('*') if _.is_file())
            dir_count = sum(1 for _ in section_path.rglob('*') if _.is_dir())
            click.echo(f"  {section_name:20} {file_count:4} files, {dir_count:3} dirs")
        else:
            click.echo(f"  {section_name:20} ❌ Not found")

def _show_detailed_status():
    """Show detailed pipeline status."""
    data_dir = Path('data')

    click.echo("📊 D4D Pipeline Status (Detailed)")
    click.echo("=" * 60)

    # Raw downloads by project
    click.echo("\n📁 Raw Downloads:")
    for project in PROJECTS:
        project_dir = data_dir / 'raw' / project
        if project_dir.exists():
            file_count = len(list(project_dir.glob('*')))
            click.echo(f"  {project:12} {file_count:4} files")
        else:
            click.echo(f"  {project:12} ⚠️  Not found")

    # Preprocessed by project
    click.echo("\n🔄 Preprocessed:")
    for project in PROJECTS:
        project_dir = data_dir / 'preprocessed' / 'individual' / project
        if project_dir.exists():
            file_count = len(list(project_dir.glob('*')))
            click.echo(f"  {project:12} {file_count:4} files")
        else:
            click.echo(f"  {project:12} ⚠️  Not found")

    # D4D Individual by method
    click.echo("\n📄 D4D Individual:")
    for method in METHODS:
        method_dir = data_dir / 'd4d_individual' / method
        if method_dir.exists():
            file_count = sum(1 for _ in method_dir.rglob('*.yaml'))
            click.echo(f"  {method:20} {file_count:4} YAML files")
        else:
            click.echo(f"  {method:20} ⚠️  Not found")

    # D4D Concatenated by method
    click.echo("\n📑 D4D Concatenated:")
    for method in METHODS:
        method_dir = data_dir / 'd4d_concatenated' / method
        if method_dir.exists():
            file_count = len(list(method_dir.glob('*.yaml')))
            click.echo(f"  {method:20} {file_count:4} YAML files")
        else:
            click.echo(f"  {method:20} ⚠️  Not found")
