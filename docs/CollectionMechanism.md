

# Class: CollectionMechanism 


_What mechanisms or procedures were used to collect the data (e.g., hardware, manual curation, software APIs)? Also covers how these mechanisms were validated._

__





URI: [data_sheets_schema:CollectionMechanism](https://w3id.org/bridge2ai/data-sheets-schema/CollectionMechanism)





```mermaid
 classDiagram
    class CollectionMechanism
    click CollectionMechanism href "../CollectionMechanism/"
      DatasetProperty <|-- CollectionMechanism
        click DatasetProperty href "../DatasetProperty/"
      
      CollectionMechanism : description
        
      CollectionMechanism : id
        
      CollectionMechanism : mechanism_details
        
      CollectionMechanism : name
        
      CollectionMechanism : used_software
        
          
    
        
        
        CollectionMechanism --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **CollectionMechanism**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [mechanism_details](mechanism_details.md) | * <br/> [String](String.md) | Details on mechanisms or procedures used to collect the data | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [collection_mechanisms](collection_mechanisms.md) | range | [CollectionMechanism](CollectionMechanism.md) |
| [DataSubset](DataSubset.md) | [collection_mechanisms](collection_mechanisms.md) | range | [CollectionMechanism](CollectionMechanism.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:CollectionMechanism |
| native | data_sheets_schema:CollectionMechanism |
| exact | rai:dataCollection |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: CollectionMechanism
description: 'What mechanisms or procedures were used to collect the data (e.g., hardware,
  manual curation, software APIs)? Also covers how these mechanisms were validated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataCollection
is_a: DatasetProperty
attributes:
  mechanism_details:
    name: mechanism_details
    description: 'Details on mechanisms or procedures used to collect the data.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - CollectionMechanism
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: CollectionMechanism
description: 'What mechanisms or procedures were used to collect the data (e.g., hardware,
  manual curation, software APIs)? Also covers how these mechanisms were validated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataCollection
is_a: DatasetProperty
attributes:
  mechanism_details:
    name: mechanism_details
    description: 'Details on mechanisms or procedures used to collect the data.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    alias: mechanism_details
    owner: CollectionMechanism
    domain_of:
    - CollectionMechanism
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: CollectionMechanism
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
    owner: CollectionMechanism
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
    owner: CollectionMechanism
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
    owner: CollectionMechanism
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>