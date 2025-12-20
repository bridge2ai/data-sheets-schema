

# Class: PreprocessingStrategy 


_Was any preprocessing of the data done (e.g., discretization or bucketing, tokenization, SIFT feature extraction)?_

__





URI: [data_sheets_schema:PreprocessingStrategy](https://w3id.org/bridge2ai/data-sheets-schema/PreprocessingStrategy)





```mermaid
 classDiagram
    class PreprocessingStrategy
    click PreprocessingStrategy href "../PreprocessingStrategy/"
      DatasetProperty <|-- PreprocessingStrategy
        click DatasetProperty href "../DatasetProperty/"
      
      PreprocessingStrategy : description
        
      PreprocessingStrategy : id
        
      PreprocessingStrategy : name
        
      PreprocessingStrategy : preprocessing_details
        
      PreprocessingStrategy : used_software
        
          
    
        
        
        PreprocessingStrategy --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **PreprocessingStrategy**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [preprocessing_details](preprocessing_details.md) | * <br/> [String](String.md) | Details on preprocessing steps applied to the data | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [preprocessing_strategies](preprocessing_strategies.md) | range | [PreprocessingStrategy](PreprocessingStrategy.md) |
| [DataSubset](DataSubset.md) | [preprocessing_strategies](preprocessing_strategies.md) | range | [PreprocessingStrategy](PreprocessingStrategy.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:PreprocessingStrategy |
| native | data_sheets_schema:PreprocessingStrategy |
| exact | rai:dataPreprocessingProtocol |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: PreprocessingStrategy
description: 'Was any preprocessing of the data done (e.g., discretization or bucketing,
  tokenization, SIFT feature extraction)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataPreprocessingProtocol
is_a: DatasetProperty
attributes:
  preprocessing_details:
    name: preprocessing_details
    description: 'Details on preprocessing steps applied to the data.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - PreprocessingStrategy
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: PreprocessingStrategy
description: 'Was any preprocessing of the data done (e.g., discretization or bucketing,
  tokenization, SIFT feature extraction)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataPreprocessingProtocol
is_a: DatasetProperty
attributes:
  preprocessing_details:
    name: preprocessing_details
    description: 'Details on preprocessing steps applied to the data.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    alias: preprocessing_details
    owner: PreprocessingStrategy
    domain_of:
    - PreprocessingStrategy
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: PreprocessingStrategy
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
    owner: PreprocessingStrategy
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
    owner: PreprocessingStrategy
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
    owner: PreprocessingStrategy
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>