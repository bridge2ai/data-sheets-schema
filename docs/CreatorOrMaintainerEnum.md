# Enum: CreatorOrMaintainerEnum 



URI: [data_sheets_schema:CreatorOrMaintainerEnum](https://w3id.org/bridge2ai/data-sheets-schema/CreatorOrMaintainerEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| data_subject | None | A person whose information is recorded in the dataset |
| third_party | None | A third party not involved in the direct creation or maintenance |
| researcher | None | A researcher involved in dataset creation or maintenance |
| industry | None | Industry professional involved in dataset creation or maintenance |
| academic_institution | None | Academic institution responsible for dataset |
| government_agency | None | Government agency responsible for dataset |
| commercial_entity | None | Commercial entity responsible for dataset |
| non_profit_organization | None | Non-profit organization responsible for dataset |
| crowdsourced | None | Dataset created through crowdsourcing efforts |
| automated_system | None | Automated system or process responsible for dataset |
| other | None | Other type of creator or maintainer not listed |








## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: CreatorOrMaintainerEnum
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  data_subject:
    text: data_subject
    description: A person whose information is recorded in the dataset.
  third_party:
    text: third_party
    description: A third party not involved in the direct creation or maintenance.
  researcher:
    text: researcher
    description: A researcher involved in dataset creation or maintenance.
  industry:
    text: industry
    description: Industry professional involved in dataset creation or maintenance.
  academic_institution:
    text: academic_institution
    description: Academic institution responsible for dataset.
  government_agency:
    text: government_agency
    description: Government agency responsible for dataset.
  commercial_entity:
    text: commercial_entity
    description: Commercial entity responsible for dataset.
  non_profit_organization:
    text: non_profit_organization
    description: Non-profit organization responsible for dataset.
  crowdsourced:
    text: crowdsourced
    description: Dataset created through crowdsourcing efforts.
  automated_system:
    text: automated_system
    description: Automated system or process responsible for dataset.
  other:
    text: other
    description: Other type of creator or maintainer not listed.

```
</details>