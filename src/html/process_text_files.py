"""Compatibility batch entry point; rendering lives in data_sheets_schema.rendering.process_text_files."""
from data_sheets_schema.rendering.process_text_files import *  # noqa: F401,F403
from data_sheets_schema.rendering import process_text_files as _implementation


def __getattr__(name):
    return getattr(_implementation, name)


def main():
    """Process all text files in data/sheets/"""

    input_dir = "data/sheets"
    output_dir = "data/sheets/html_output"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Find YAML files
    yaml_files = sorted(p.name for p in Path(input_dir).glob("*.yaml"))

    processed_count = 0

    for yaml_file in yaml_files:
        yaml_path = os.path.join(input_dir, yaml_file)
        if os.path.exists(yaml_path):
            if process_text_file(yaml_path, output_dir):
                processed_count += 1
        else:
            print(f"File not found: {yaml_path}")

    print(f"\nProcessing complete! Processed {processed_count} YAML files.")
    print(f"HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
