"""Compatibility batch entry point; rendering lives in data_sheets_schema.rendering.human_readable_renderer."""
from data_sheets_schema.rendering.human_readable_renderer import *  # noqa: F401,F403
from data_sheets_schema.rendering import human_readable_renderer as _implementation


def __getattr__(name):
    return getattr(_implementation, name)


def main():
    """Process all YAML files and generate human-readable HTML versions"""

    input_dir = "data/sheets/html_output"
    output_dir = "src/html/output"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Process YAML data files
    yaml_files = sorted(p.name for p in Path(input_dir).glob("*.yaml"))

    processed_count = 0

    for yaml_file in yaml_files:
        yaml_path = os.path.join(input_dir, yaml_file)
        if os.path.exists(yaml_path):
            if process_yaml_file(yaml_path, output_dir):
                processed_count += 1
        else:
            print(f"File not found: {yaml_path}")

    print(f"\nProcessed {processed_count} files.")
    print(f"Human-readable HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
