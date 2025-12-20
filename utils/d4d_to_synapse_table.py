"""
d4d_to_synapse_table.py

"""
import os
import csv
import pandas as pd
import synapseclient
from synapseclient import Column, Schema, Table
import sys

def add_css(css_name: str, source_folder: str, d4d_dict: dict[str, list[str]]) -> dict[str, list[str]]:
	"""Add CSS content to the D4D dictionary."""

	css_path = os.path.join(source_folder, css_name)
	
	if os.path.exists(css_path):
		with open(css_path, 'r') as css_file:
			css_text = css_file.read()
		d4d_dict["content_type"].append("css")
		d4d_dict["content_id"].append("")
		d4d_dict["content_text"].append(css_text)

	return d4d_dict


def add_html(file_org_map: dict[str, str], source_folder: str, html_name_parts: str, d4d_dict: dict[str, list[str]]) -> dict[str, list[str]]:
	"""Add HTML content to the D4D dictionary."""

	for org, id in file_org_map.items():
		html_path = os.path.join(source_folder, "".join([html_name_parts[0], org, html_name_parts[1]]))
		if os.path.exists(html_path):
			with open(html_path, 'r') as html_file:
				d4d_text = html_file.read()
			d4d_dict["content_type"].append("html")
			d4d_dict["content_id"].append(id)
			d4d_dict["content_text"].append(d4d_text)

	return d4d_dict


def create_d4d_df(d4d_dict: dict[str, list[str]]) -> pd.DataFrame:
	"""Create a DataFrame from the D4D dictionary."""
	return pd.DataFrame.from_dict(d4d_dict)


def generate_table(syn, table_name: str, table_id: str|None, project_id: str, d4d_df: pd.DataFrame) -> Table:
	"""Generate a Synapse table from the D4D DataFrame."""

	table_cols = [  # Define table columns
			Column(name="content_type", columnType="STRING"),
			Column(name="content_id", columnType="STRING", maximumSize=30),
			Column(name="content_text", columnType="LARGETEXT")
		]
	
	# Generate table schema
	table_schema = Schema(name=table_name, columns=table_cols, parent=project_id)

	if table_id is not None:
		csv.field_size_limit(sys.maxsize)
		existing_rows = syn.tableQuery(f"select * from {table_id}")
		syn.delete(existing_rows)

	d4d_table = Table(schema=table_schema, values=d4d_df)
	syn.store(d4d_table)
	syn.create_snapshot_version(table_id)

	return d4d_table


def main():
	"""Main function to extract D4D info and upload to Synapse"""

	syn = synapseclient.login()
	
	project_id = "syn63096806"  # standards-data Synapse project ID
	table_id = "syn68885644"  # if provided, the table associated with this ID will be cleared before being updated with new entries
	table_name = "D4D_content"  # if table_id was provided, table_name should match the name of the table associated with table_id
	source_folder = "src/html/output"  # folder containing HTML and CSS files
	html_name_parts = ["D4D_-_", "_v4_human_readable.html"]  # joined with org name in in org_id_map to create HTML paths
	css_name = "datasheet-common.css"  # since a single CSS is in use, no need to select multiple or build distinct paths

	d4d_dict = {  # initialize dict to store D4D info
		"content_type": [],
		"content_id": [],
		"content_text": []
		}
    
	org_id_map = {  # define relationships between GC labels and ORG_IDs
		"AI-READI": "B2AI_ORG:114",
		"CM4AI": "B2AI_ORG:116",
		"VOICE": "B2AI_ORG:117",
		"CHORUS": "B2AI_ORG:115"
	}

	updated_d4d_dict = add_css(css_name, source_folder, d4d_dict)
	final_d4d_dict = add_html(org_id_map, source_folder, html_name_parts, updated_d4d_dict)
	d4d_df = create_d4d_df(final_d4d_dict)
	generate_table(syn, table_name, table_id, project_id, d4d_df)
	
if __name__ == "__main__":
    main() 