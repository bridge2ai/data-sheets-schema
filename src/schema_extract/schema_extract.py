#!/usr/bin/env python3
"""
schema_extract.py

A script that:
1. Reads an input text (or JSON) document.
2. Loads one or more LinkML YAML schemas from a directory.
3. Uses a fallback implementation (simulating an older langgraph API) to extract information from the text.
4. Populates schema fields according to each schema’s class definition.
5. Saves each populated schema instance as YAML.

Requirements:
  pip install openai linkml-runtime pyyaml

Usage (example):
  python schema_extract.py ../../../CM4AI_docs_for_D4D/cm4ai_chromatin_mda-mb-468_untreated_apms_0.1_alpha/ro-crate-metadata.json ../data_sheets_schema/schema/modules/ ./ <open ai key>
"""

import os
import yaml
import openai
import argparse
from typing import Any, Dict

# -----------------------------------------------------------------------------
# Fallback implementations to simulate the older langgraph API
# -----------------------------------------------------------------------------
class Prompt:
    def __init__(self, name: str, prompt: str, model: str, temperature: float):
        self.name = name
        self.prompt = prompt
        self.model = model
        self.temperature = temperature

class ChatGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def run(self) -> Dict[str, str]:
        responses = {}
        # For each node (we expect just one), call the new OpenAI ChatCompletion API.
        for node in self.nodes:
            response = openai.ChatCompletion.create(
                model=node.model,
                messages=[{"role": "user", "content": node.prompt}],
                temperature=node.temperature,
            )
            # Extract the assistant's reply text
            text = response["choices"][0]["message"]["content"]
            responses[node.name] = text
        return responses

# -----------------------------------------------------------------------------
# LinkML Imports
# -----------------------------------------------------------------------------
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.linkml_model.meta import SchemaDefinition, ClassDefinition, SlotDefinition

# -----------------------------------------------------------------------------
# Functions for schema extraction and instance population
# -----------------------------------------------------------------------------
def load_linkml_schema(schema_path: str) -> SchemaDefinition:
    """
    Loads a LinkML schema from a YAML file and returns a SchemaDefinition object.
    """
    return SchemaView(schema_path).schema

def build_extraction_prompt(text: str, schema: SchemaDefinition, class_name: str) -> str:
    """
    Builds a natural language prompt instructing GPT to extract structured data
    for a given LinkML class. Lists all slot (field) names and their descriptions.
    """
    cls_def: ClassDefinition = schema.classes[class_name]
    slot_prompts = []
    for slot_name in cls_def.slots:
        slot_def: SlotDefinition = schema.slots[slot_name]
        slot_range = slot_def.range if slot_def.range else "string"
        desc = slot_def.description or ""
        slot_prompts.append(f"- {slot_name} ({slot_range}): {desc}")
    
    prompt_template = f"""
You are a helpful assistant that extracts structured data from text.

Given the following text, please extract the relevant information for the schema class: {class_name}.

Text:
{text}

We have these fields to fill (in JSON format):
{os.linesep.join(slot_prompts)}

Return your answer in valid JSON with the fields as keys.
If a field doesn't exist in the text, use null or an empty string.
    """
    return prompt_template.strip()

def call_gpt_with_langgraph(prompt: str, model_name: str = "gpt-3.5-turbo") -> str:
    """
    Uses our fallback ChatGraph + Prompt implementation to call GPT with a single prompt.
    Returns the raw text response from the model.
    """
    graph = ChatGraph(
        nodes=[
            Prompt(
                name="extract_data",
                prompt=prompt,
                model=model_name,
                temperature=0.0,
            )
        ]
    )
    response = graph.run()
    return response["extract_data"]

def parse_json_response(response: str) -> Dict[str, Any]:
    """
    Attempts to parse the GPT response as JSON (or YAML).
    If it fails, returns an empty dictionary.
    """
    try:
        data = yaml.safe_load(response)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}

def fill_schema_instance(schema: SchemaDefinition, class_name: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps the extracted JSON data into a dictionary conforming to the schema’s class.
    If the GPT output doesn't have a needed slot, defaults to None.
    """
    cls_def: ClassDefinition = schema.classes[class_name]
    instance_data = {}
    for slot_name in cls_def.slots:
        val = extracted_data.get(slot_name, None)
        instance_data[slot_name] = val
    return {class_name: instance_data}

def process_schema(text: str, schema_path: str, output_dir: str, model_name: str = "gpt-3.5-turbo"):
    """
    For a single schema:
      - Load the schema
      - Select a top-level class (first by default)
      - Build a prompt and send it to GPT via our fallback ChatGraph
      - Parse the result and create a LinkML instance
      - Save the instance as YAML
    """
    print(f"Processing schema: {schema_path} ...")
    schema = load_linkml_schema(schema_path)
    class_names = list(schema.classes.keys())
    if not class_names:
        print(f"No classes found in {schema_path}")
        return
    # For demonstration, use the first class in the schema
    class_name = class_names[0]
    print(f"Extracting data for class: {class_name}")
    
    prompt = build_extraction_prompt(text, schema, class_name)
    response = call_gpt_with_langgraph(prompt, model_name=model_name)
    extracted_data = parse_json_response(response)
    instance_dict = fill_schema_instance(schema, class_name, extracted_data)
    
    base_name = os.path.splitext(os.path.basename(schema_path))[0]
    out_file = os.path.join(output_dir, f"{base_name}_instance.yaml")
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(instance_dict, f, sort_keys=False)
    print(f"Saved instance to {out_file}")

def main(input_text_path: str, schemas_dir: str, output_dir: str, model_name: str = "gpt-3.5-turbo"):
    """
    Main routine:
      - Reads the input text file
      - Finds all schemas in schemas_dir
      - Processes each schema
      - Saves all outputs in output_dir
    """
    with open(input_text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    os.makedirs(output_dir, exist_ok=True)
    
    schema_files = [f for f in os.listdir(schemas_dir) if f.lower().endswith((".yaml", ".yml"))]
    for schema_file in schema_files:
        schema_path = os.path.join(schemas_dir, schema_file)
        process_schema(text, schema_path, output_dir, model_name=model_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract schema data from an input text file using OpenAI GPT."
    )
    parser.add_argument(
        "input_text_path",
        type=str,
        help="Path to the input text (or JSON) file."
    )
    parser.add_argument(
        "schemas_dir",
        type=str,
        help="Directory containing LinkML YAML schemas."
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Directory where the generated instance files will be saved."
    )
    parser.add_argument(
        "openai_api_key",
        type=str,
        help="Your OpenAI API key."
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="gpt-3.5-turbo",
        help="The OpenAI model to use (default: gpt-3.5-turbo)."
    )

    args = parser.parse_args()

    # Set the OpenAI API key
    openai.api_key = args.openai_api_key

    main(
        input_text_path=args.input_text_path,
        schemas_dir=args.schemas_dir,
        output_dir=args.output_dir,
        model_name=args.model_name
    )

