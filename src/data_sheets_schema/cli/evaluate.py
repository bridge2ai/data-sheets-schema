"""Evaluate command group for D4D CLI.

Commands for evaluating D4D datasheet quality.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import PROJECTS, METHODS, RUBRIC_TYPES
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

@click.group()
def evaluate():
    """D4D evaluation commands."""
    pass

@evaluate.command()
@click.option('--project', type=click.Choice(PROJECTS),
              help='Evaluate specific project only (default: all)')
@click.option('--method', type=click.Choice(METHODS), default='gpt5',
              help='Method to evaluate')
@click.option('--output-dir', type=click.Path(), default='data/evaluation',
              help='Output directory for evaluation reports')
def presence(project, method, output_dir):
    """Run presence-based evaluation (field existence check)."""
    require_repo_context("d4d evaluate presence")

    if project:
        click.echo(f"📊 Evaluating {project} ({method}) - presence-based...")
    else:
        click.echo(f"📊 Evaluating all projects ({method}) - presence-based...")

    # Import and call the evaluation script
    setup_repo_imports()
    from src.evaluation.evaluate_d4d import main as eval_main

    # Set up args for the evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d.py',
                '--methods', method,
                '--output-dir', output_dir]
    if project:
        sys.argv.extend(['--project', project])

    try:
        eval_main()
        click.echo(f"✓ Evaluation complete. Reports saved to {output_dir}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv

@evaluate.command()
@click.option('--file', type=click.Path(exists=True), required=True,
              help='D4D YAML file to evaluate')
@click.option('--project', type=click.Choice(PROJECTS), required=True,
              help='Project name')
@click.option('--method', type=click.Choice(METHODS), required=True,
              help='Generation method')
@click.option('--rubric', type=click.Choice(RUBRIC_TYPES + ['both']),
              default='both',
              help='Which rubric to use')
@click.option('--output-dir', type=click.Path(), default='data/evaluation_llm',
              help='Output directory for LLM evaluation reports')
def llm(file, project, method, rubric, output_dir):
    """Run LLM-based quality evaluation (requires ANTHROPIC_API_KEY)."""
    require_repo_context("d4d evaluate llm")

    click.echo(f"🤖 LLM evaluating {file} with {rubric}...")
    click.echo("⚠️  Note: Requires ANTHROPIC_API_KEY environment variable")

    # Import and call the LLM evaluation script
    setup_repo_imports()

    try:
        from src.evaluation.evaluate_d4d_llm import main as llm_eval_main
    except ImportError:
        click.echo("❌ Error: LLM evaluation script not found", err=True)
        click.echo("   Expected: src/evaluation/evaluate_d4d_llm.py", err=True)
        sys.exit(1)

    # Set up args for the LLM evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d_llm.py',
                '--file', file,
                '--project', project,
                '--method', method,
                '--rubric', rubric,
                '--output-dir', output_dir]

    try:
        llm_eval_main()
        click.echo(f"✓ LLM evaluation complete. Reports saved to {output_dir}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv
