"""Compatibility batch entry point; rendering lives in data_sheets_schema.rendering.rubric20_semantic."""
from data_sheets_schema.rendering.rubric20_semantic import *  # noqa: F401,F403
from data_sheets_schema.rendering import rubric20_semantic as _implementation


def __getattr__(name):
    return getattr(_implementation, name)


def main():
    """Process rubric20-semantic claudecode_agent evaluation JSON files and generate HTML"""

    input_dir = Path("data/evaluation_llm/rubric20/concatenated")
    if not input_dir.exists():
        input_dir = Path("data/evaluation_llm/rubric20_semantic/concatenated")
    output_dir = Path("data/d4d_html/concatenated/claudecode_agent")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find claudecode_agent evaluation files
    eval_files = sorted(input_dir.glob("*claudecode_agent_evaluation.json"))

    if not eval_files:
        print(f"No claudecode_agent evaluation files found in {input_dir}")
        return

    print(f"Found {len(eval_files)} evaluation files to render")
    print(f"Output directory: {output_dir}\n")

    processed_count = 0

    for eval_file in eval_files:
        print(f"Processing: {eval_file.name}")

        try:
            # Read JSON
            with open(eval_file, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)

            # Generate output filename
            project_name = eval_file.stem.replace('_claudecode_agent_evaluation', '')
            output_path = output_dir / f"{project_name}_evaluation_rubric20.html"

            # Generate HTML
            generate_evaluation_html(eval_data, output_path)

            print(f"  ✅ Generated: {output_path}")
            processed_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {eval_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Processed {processed_count}/{len(eval_files)} files successfully")
    print(f"HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
