

# Class: FundingMechanism 


_Who funded the creation of the dataset? If there is an associated grant, please provide the name of the grantor and the grant name and number._

__





URI: [data_sheets_schema:FundingMechanism](https://w3id.org/bridge2ai/data-sheets-schema/FundingMechanism)





```mermaid
 classDiagram
    class FundingMechanism
    click FundingMechanism href "../FundingMechanism/"
      DatasetProperty <|-- FundingMechanism
        click DatasetProperty href "../DatasetProperty/"
      
      FundingMechanism : description
        
      FundingMechanism : grantor
        
          
    
        
        
        FundingMechanism --> "0..1" Grantor : grantor
        click Grantor href "../Grantor/"
    

        
      FundingMechanism : grants
        
          
    
        
        
        FundingMechanism --> "*" Grant : grants
        click Grant href "../Grant/"
    

        
      FundingMechanism : id
        
      FundingMechanism : name
        
      FundingMechanism : used_software
        
          
    
        
        
        FundingMechanism --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **FundingMechanism**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [grantor](grantor.md) | 0..1 <br/> [Grantor](Grantor.md) | Name/identifier of the organization providing monetary or resource support | direct |
| [grants](grants.md) | * <br/> [Grant](Grant.md) | Grant mechanisms supporting dataset creation | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [funders](funders.md) | range | [FundingMechanism](FundingMechanism.md) |
| [DataSubset](DataSubset.md) | [funders](funders.md) | range | [FundingMechanism](FundingMechanism.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:FundingMechanism |
| native | data_sheets_schema:FundingMechanism |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: FundingMechanism
description: 'Who funded the creation of the dataset? If there is an associated grant,
  please provide the name of the grantor and the grant name and number.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  grantor:
    name: grantor
    description: Name/identifier of the organization providing monetary or resource
      support.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    slot_uri: schema:funder
    domain_of:
    - FundingMechanism
    range: Grantor
  grants:
    name: grants
    description: Grant mechanisms supporting dataset creation. Multiple grants may
      fund a single dataset.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    slot_uri: schema:funding
    domain_of:
    - FundingMechanism
    range: Grant
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>

### Induced

<details>
```yaml
name: FundingMechanism
description: 'Who funded the creation of the dataset? If there is an associated grant,
  please provide the name of the grantor and the grant name and number.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  grantor:
    name: grantor
    description: Name/identifier of the organization providing monetary or resource
      support.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    slot_uri: schema:funder
    alias: grantor
    owner: FundingMechanism
    domain_of:
    - FundingMechanism
    range: Grantor
  grants:
    name: grants
    description: Grant mechanisms supporting dataset creation. Multiple grants may
      fund a single dataset.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    slot_uri: schema:funding
    alias: grants
    owner: FundingMechanism
    domain_of:
    - FundingMechanism
    range: Grant
    multivalued: true
    inlined: true
    inlined_as_list: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: FundingMechanism
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
    owner: FundingMechanism
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
    owner: FundingMechanism
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
    owner: FundingMechanism
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>