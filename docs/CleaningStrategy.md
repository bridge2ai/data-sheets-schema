

# Class: CleaningStrategy 


_Was any cleaning of the data done (e.g., removal of instances, processing of missing values)?_

__





URI: [data_sheets_schema:CleaningStrategy](https://w3id.org/bridge2ai/data-sheets-schema/CleaningStrategy)





```mermaid
 classDiagram
    class CleaningStrategy
    click CleaningStrategy href "../CleaningStrategy/"
      DatasetProperty <|-- CleaningStrategy
        click DatasetProperty href "../DatasetProperty/"
      
      CleaningStrategy : cleaning_details
        
      CleaningStrategy : description
        
      CleaningStrategy : id
        
      CleaningStrategy : name
        
      CleaningStrategy : used_software
        
          
    
        
        
        CleaningStrategy --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **CleaningStrategy**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [cleaning_details](cleaning_details.md) | * <br/> [String](String.md) | Details on data cleaning procedures applied | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [cleaning_strategies](cleaning_strategies.md) | range | [CleaningStrategy](CleaningStrategy.md) |
| [DataSubset](DataSubset.md) | [cleaning_strategies](cleaning_strategies.md) | range | [CleaningStrategy](CleaningStrategy.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:CleaningStrategy |
| native | data_sheets_schema:CleaningStrategy |
| exact | rai:dataManipulationProtocol |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: CleaningStrategy
description: 'Was any cleaning of the data done (e.g., removal of instances, processing
  of missing values)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataManipulationProtocol
is_a: DatasetProperty
attributes:
  cleaning_details:
    name: cleaning_details
    description: 'Details on data cleaning procedures applied.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - CleaningStrategy
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: CleaningStrategy
description: 'Was any cleaning of the data done (e.g., removal of instances, processing
  of missing values)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataManipulationProtocol
is_a: DatasetProperty
attributes:
  cleaning_details:
    name: cleaning_details
    description: 'Details on data cleaning procedures applied.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    alias: cleaning_details
    owner: CleaningStrategy
    domain_of:
    - CleaningStrategy
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: CleaningStrategy
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
    owner: CleaningStrategy
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
    owner: CleaningStrategy
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
    owner: CleaningStrategy
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>