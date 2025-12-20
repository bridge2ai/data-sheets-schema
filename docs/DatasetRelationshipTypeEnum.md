# Enum: DatasetRelationshipTypeEnum 




_Standardized types of relationships between datasets, based on DataCite Metadata Schema RelationType controlled vocabulary and Dublin Core relationship terms. See https://datacite-metadata-schema.readthedocs.io/ and http://purl.org/dc/terms/_



URI: [data_sheets_schema:DatasetRelationshipTypeEnum](https://w3id.org/bridge2ai/data-sheets-schema/DatasetRelationshipTypeEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| derives_from | None | This dataset is derived from the target dataset through processing, analysis,... |
| supplements | None | This dataset supplements or adds to the target dataset |
| is_supplemented_by | None | This dataset is supplemented by the target dataset |
| is_version_of | None | This dataset is a version of the target dataset (e |
| is_new_version_of | None | This dataset is a new version that replaces or updates the target dataset |
| replaces | None | This dataset replaces or supersedes the target dataset |
| is_replaced_by | None | This dataset is replaced or superseded by the target dataset |
| is_required_by | None | This dataset is required by the target dataset |
| requires | None | This dataset requires the target dataset |
| is_part_of | None | This dataset is part of the target dataset (e |
| has_part | None | This dataset has the target dataset as a part |
| is_referenced_by | None | This dataset is referenced or cited by the target dataset |
| references | None | This dataset references or cites the target dataset |
| is_identical_to | None | This dataset is identical to the target dataset (e |




## Slots

| Name | Description |
| ---  | --- |
| [relationship_type](relationship_type.md) | The type of relationship (e |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: DatasetRelationshipTypeEnum
description: Standardized types of relationships between datasets, based on DataCite
  Metadata Schema RelationType controlled vocabulary and Dublin Core relationship
  terms. See https://datacite-metadata-schema.readthedocs.io/ and http://purl.org/dc/terms/
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  derives_from:
    text: derives_from
    description: This dataset is derived from the target dataset through processing,
      analysis, or transformation. Equivalent to DataCite IsDerivedFrom.
    broad_mappings:
    - dcterms:source
  supplements:
    text: supplements
    description: This dataset supplements or adds to the target dataset. Equivalent
      to DataCite IsSupplementTo.
    broad_mappings:
    - dcterms:relation
  is_supplemented_by:
    text: is_supplemented_by
    description: This dataset is supplemented by the target dataset. Equivalent to
      DataCite IsSupplementedBy.
    broad_mappings:
    - dcterms:relation
  is_version_of:
    text: is_version_of
    description: This dataset is a version of the target dataset (e.g., updated, corrected,
      or revised version). Equivalent to DataCite IsVersionOf.
    exact_mappings:
    - dcterms:isVersionOf
  is_new_version_of:
    text: is_new_version_of
    description: This dataset is a new version that replaces or updates the target
      dataset. Equivalent to DataCite IsNewVersionOf.
    exact_mappings:
    - dcterms:isVersionOf
    broad_mappings:
    - dcterms:replaces
  replaces:
    text: replaces
    description: This dataset replaces or supersedes the target dataset. Equivalent
      to DataCite Obsoletes.
    exact_mappings:
    - dcterms:replaces
  is_replaced_by:
    text: is_replaced_by
    description: This dataset is replaced or superseded by the target dataset. Equivalent
      to DataCite IsObsoletedBy.
    exact_mappings:
    - dcterms:isReplacedBy
  is_required_by:
    text: is_required_by
    description: This dataset is required by the target dataset. Equivalent to DataCite
      IsRequiredBy.
    exact_mappings:
    - dcterms:isRequiredBy
  requires:
    text: requires
    description: This dataset requires the target dataset. Equivalent to DataCite
      Requires.
    exact_mappings:
    - dcterms:requires
  is_part_of:
    text: is_part_of
    description: This dataset is part of the target dataset (e.g., subset, component).
      Equivalent to DataCite IsPartOf.
    exact_mappings:
    - dcterms:isPartOf
  has_part:
    text: has_part
    description: This dataset has the target dataset as a part. Equivalent to DataCite
      HasPart.
    exact_mappings:
    - dcterms:hasPart
  is_referenced_by:
    text: is_referenced_by
    description: This dataset is referenced or cited by the target dataset. Equivalent
      to DataCite IsReferencedBy.
    exact_mappings:
    - dcterms:isReferencedBy
  references:
    text: references
    description: This dataset references or cites the target dataset. Equivalent to
      DataCite References.
    exact_mappings:
    - dcterms:references
  is_identical_to:
    text: is_identical_to
    description: This dataset is identical to the target dataset (e.g., mirror, copy).
      Equivalent to DataCite IsIdenticalTo.
    broad_mappings:
    - dcterms:relation

```
</details>