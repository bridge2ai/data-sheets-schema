

# Class: ExternalResource 


_Is the dataset self-contained or does it rely on external resources (e.g., websites, other datasets)? If external, are there guarantees that those resources will remain available and unchanged?_

__





URI: [data_sheets_schema:ExternalResource](https://w3id.org/bridge2ai/data-sheets-schema/ExternalResource)





```mermaid
 classDiagram
    class ExternalResource
    click ExternalResource href "../ExternalResource/"
      DatasetProperty <|-- ExternalResource
        click DatasetProperty href "../DatasetProperty/"
      
      ExternalResource : archival
        
      ExternalResource : description
        
      ExternalResource : external_resources
        
      ExternalResource : future_guarantees
        
      ExternalResource : id
        
      ExternalResource : name
        
      ExternalResource : restrictions
        
      ExternalResource : used_software
        
          
    
        
        
        ExternalResource --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **ExternalResource**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [external_resources](external_resources.md) | * <br/> [String](String.md) | List of links or identifiers for external resources | direct |
| [future_guarantees](future_guarantees.md) | * <br/> [String](String.md) | Explanation of any commitments that external resources will remain available ... | direct |
| [archival](archival.md) | * <br/> [Boolean](Boolean.md) | Indication whether official archival versions of external resources are inclu... | direct |
| [restrictions](restrictions.md) | * <br/> [String](String.md) | Description of any restrictions or fees associated with external resources | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [external_resources](external_resources.md) | range | [ExternalResource](ExternalResource.md) |
| [DataSubset](DataSubset.md) | [external_resources](external_resources.md) | range | [ExternalResource](ExternalResource.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:ExternalResource |
| native | data_sheets_schema:ExternalResource |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ExternalResource
description: 'Is the dataset self-contained or does it rely on external resources
  (e.g., websites, other datasets)? If external, are there guarantees that those resources
  will remain available and unchanged?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
slots:
- external_resources
slot_usage:
  external_resources:
    name: external_resources
    description: List of links or identifiers for external resources.
    range: string
attributes:
  future_guarantees:
    name: future_guarantees
    description: 'Explanation of any commitments that external resources will remain
      available and stable over time.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - ExternalResource
    range: string
    multivalued: true
  archival:
    name: archival
    description: 'Indication whether official archival versions of external resources
      are included.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - ExternalResource
    range: boolean
    multivalued: true
  restrictions:
    name: restrictions
    description: 'Description of any restrictions or fees associated with external
      resources.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:accessRights
    domain_of:
    - ExternalResource
    - IPRestrictions
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ExternalResource
description: 'Is the dataset self-contained or does it rely on external resources
  (e.g., websites, other datasets)? If external, are there guarantees that those resources
  will remain available and unchanged?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
slot_usage:
  external_resources:
    name: external_resources
    description: List of links or identifiers for external resources.
    range: string
attributes:
  future_guarantees:
    name: future_guarantees
    description: 'Explanation of any commitments that external resources will remain
      available and stable over time.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: future_guarantees
    owner: ExternalResource
    domain_of:
    - ExternalResource
    range: string
    multivalued: true
  archival:
    name: archival
    description: 'Indication whether official archival versions of external resources
      are included.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: archival
    owner: ExternalResource
    domain_of:
    - ExternalResource
    range: boolean
    multivalued: true
  restrictions:
    name: restrictions
    description: 'Description of any restrictions or fees associated with external
      resources.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:accessRights
    alias: restrictions
    owner: ExternalResource
    domain_of:
    - ExternalResource
    - IPRestrictions
    range: string
    multivalued: true
  external_resources:
    name: external_resources
    description: List of links or identifiers for external resources.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:references
    alias: external_resources
    owner: ExternalResource
    domain_of:
    - Dataset
    - ExternalResource
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: ExternalResource
    domain_of:
    - NamedThing
    - DatasetProperty
    range: uriorcurie
  name:
    name: name
    description: A human-readable name for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:name
    alias: name
    owner: ExternalResource
    domain_of:
    - NamedThing
    - DatasetProperty
    range: string
  description:
    name: description
    description: A human-readable description for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:description
    alias: description
    owner: ExternalResource
    domain_of:
    - NamedThing
    - DatasetProperty
    - DatasetRelationship
    range: string
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: ExternalResource
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>