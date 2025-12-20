# Enum: DataUsePermissionEnum 




_Data use permissions and restrictions based on the Data Use Ontology (DUO). DUO is a standardized ontology for representing data use conditions developed by GA4GH. See https://github.com/EBISPOT/DUO_



URI: [data_sheets_schema:DataUsePermissionEnum](https://w3id.org/bridge2ai/data-sheets-schema/DataUsePermissionEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| no_restriction | DUO:0000004 | No restriction on data use |
| general_research_use | DUO:0000042 | Data available for any research purpose (GRU) |
| health_medical_biomedical_research | DUO:0000006 | Data limited to health, medical, or biomedical research (HMB) |
| disease_specific_research | DUO:0000007 | Data limited to research on specified disease(s) (DS) |
| population_origins_ancestry_research | DUO:0000011 | Data limited to population origins or ancestry research (POA) |
| clinical_care_use | DUO:0000043 | Data available for clinical care and applications (CC) |
| no_commercial_use | DUO:0000046 | Data use limited to non-commercial purposes (NCU) |
| non_profit_use_only | DUO:0000045 | Data use limited to not-for-profit organizations (NPU) |
| non_profit_use_and_non_commercial_use | DUO:0000018 | Data limited to not-for-profit organizations and non-commercial use (NPUNCU) |
| no_methods_development | DUO:0000015 | Data cannot be used for methods or software development (NMDS) |
| genetic_studies_only | DUO:0000016 | Data limited to genetic studies only (GSO) |
| ethics_approval_required | DUO:0000021 | Ethics approval (e |
| collaboration_required | DUO:0000020 | Collaboration with primary investigator required (COL) |
| publication_required | DUO:0000019 | Results must be published/shared with research community (PUB) |
| geographic_restriction | DUO:0000022 | Data use limited to specific geographic region (GS) |
| institution_specific | DUO:0000028 | Data use limited to approved institutions (IS) |
| project_specific | DUO:0000027 | Data use limited to approved project(s) (PS) |
| user_specific | DUO:0000026 | Data use limited to approved users (US) |
| time_limit | DUO:0000025 | Data use approved for limited time period (TS) |
| return_to_database | DUO:0000029 | Derived data must be returned to database/resource (RTN) |
| publication_moratorium | DUO:0000024 | Publication restricted until specified date (MOR) |
| no_population_ancestry_research | DUO:0000044 | Population/ancestry research prohibited (NPOA) |




## Slots

| Name | Description |
| ---  | --- |
| [data_use_permission](data_use_permission.md) | Structured data use permissions using the Data Use Ontology (DUO) |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: DataUsePermissionEnum
description: Data use permissions and restrictions based on the Data Use Ontology
  (DUO). DUO is a standardized ontology for representing data use conditions developed
  by GA4GH. See https://github.com/EBISPOT/DUO
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  no_restriction:
    text: no_restriction
    description: No restriction on data use
    meaning: DUO:0000004
  general_research_use:
    text: general_research_use
    description: Data available for any research purpose (GRU)
    meaning: DUO:0000042
  health_medical_biomedical_research:
    text: health_medical_biomedical_research
    description: Data limited to health, medical, or biomedical research (HMB)
    meaning: DUO:0000006
  disease_specific_research:
    text: disease_specific_research
    description: Data limited to research on specified disease(s) (DS)
    meaning: DUO:0000007
  population_origins_ancestry_research:
    text: population_origins_ancestry_research
    description: Data limited to population origins or ancestry research (POA)
    meaning: DUO:0000011
  clinical_care_use:
    text: clinical_care_use
    description: Data available for clinical care and applications (CC)
    meaning: DUO:0000043
  no_commercial_use:
    text: no_commercial_use
    description: Data use limited to non-commercial purposes (NCU)
    meaning: DUO:0000046
  non_profit_use_only:
    text: non_profit_use_only
    description: Data use limited to not-for-profit organizations (NPU)
    meaning: DUO:0000045
  non_profit_use_and_non_commercial_use:
    text: non_profit_use_and_non_commercial_use
    description: Data limited to not-for-profit organizations and non-commercial use
      (NPUNCU)
    meaning: DUO:0000018
  no_methods_development:
    text: no_methods_development
    description: Data cannot be used for methods or software development (NMDS)
    meaning: DUO:0000015
  genetic_studies_only:
    text: genetic_studies_only
    description: Data limited to genetic studies only (GSO)
    meaning: DUO:0000016
  ethics_approval_required:
    text: ethics_approval_required
    description: Ethics approval (e.g., IRB/ERB) required for data use (IRB)
    meaning: DUO:0000021
  collaboration_required:
    text: collaboration_required
    description: Collaboration with primary investigator required (COL)
    meaning: DUO:0000020
  publication_required:
    text: publication_required
    description: Results must be published/shared with research community (PUB)
    meaning: DUO:0000019
  geographic_restriction:
    text: geographic_restriction
    description: Data use limited to specific geographic region (GS)
    meaning: DUO:0000022
  institution_specific:
    text: institution_specific
    description: Data use limited to approved institutions (IS)
    meaning: DUO:0000028
  project_specific:
    text: project_specific
    description: Data use limited to approved project(s) (PS)
    meaning: DUO:0000027
  user_specific:
    text: user_specific
    description: Data use limited to approved users (US)
    meaning: DUO:0000026
  time_limit:
    text: time_limit
    description: Data use approved for limited time period (TS)
    meaning: DUO:0000025
  return_to_database:
    text: return_to_database
    description: Derived data must be returned to database/resource (RTN)
    meaning: DUO:0000029
  publication_moratorium:
    text: publication_moratorium
    description: Publication restricted until specified date (MOR)
    meaning: DUO:0000024
  no_population_ancestry_research:
    text: no_population_ancestry_research
    description: Population/ancestry research prohibited (NPOA)
    meaning: DUO:0000044

```
</details>