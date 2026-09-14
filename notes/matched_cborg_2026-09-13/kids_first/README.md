# Kids First source bundle — 2026-09-13

The external canary documents the Kids First Data Resource. The captured public DRC catalogue has 36 distinct study accessions; every entry has a captured public dbGaP description and a linked project or investigator abstract. This is a snapshot of that catalogue, not an assertion that every funded award has released data.

The bundle contains 55 source documents: article metadata/abstract, resource and access guides, NIH award-abstract pages, public descriptions for the 36 studies, and the catalogue fields and links. It uses the neutral profile. API and agentic canaries must receive these same frozen bytes.

- [Source manifest](manifest.yaml)
- [Participating-study metadata and links](study_catalogue.json)
- [Processing and source hashes](extraction.json)
- [Chunk-to-source mapping](chunks.yaml)
- [Trusted applicability context](applicability.yaml)

Bundle: `KIDS_FIRST_preprocessed.txt`; 541,184 bytes; 58 chunks; SHA256 `cc45c89548158a7a909699fbf1f75e6cc88c32ac8486d5518c5d4e46cdc9447c`.

The article is [The Gabriella Miller Kids First Data Resource for genomic research in pediatric cancer and congenital anomalies](https://doi.org/10.1016/j.ajhg.2026.07.010), PMID 42607672. Europe PMC supplies its indexed abstract and metadata. The publisher confirms the DOI and open-access flag; its website returned HTTP 403 and its full-text API view returned HTTP 401 in this environment. **The full article was not captured.** Metadata-only publisher responses and failed responses are excluded from the model input. Adding the full article later changes the registered source condition.

Public documentation originals remain locally preserved with URL/date/SHA256 capture receipts. The versioned model input contains the declared extracted documentation and aggregate study metadata. Historical catalogue release-note fields containing individual sample-identifier mappings, data files, and authorized-request listings are excluded. Hyperlink targets are retained.

Adult VOICE and VOICE-Pediatric remain separate study-cohort datasets, using their existing downloads; neither belongs to this external bundle.

## Participating datasets in the captured catalogue

Catalogue and dbGaP titles are both retained in the source files. A broader or renamed current dbGaP record must not silently replace the catalogue-specific cohort scope.

| Catalogue dataset | dbGaP documentation | Project / abstract | Latest release stated by catalogue |
|---|---|---|---|
| Kids First: Congenital Diaphragmatic Hernia | [phs001110.v4.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001110.v4.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Chung) | Jun 12, 2025 |
| Kids First: Whole genome sequencing studies of multiplex nonsyndromic cleft lip/palate families | [phs002626.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002626.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2021X01projects#FY21_Letra) | Apr 24, 2025 |
| Kids First: T-Cell ALL | [phs002276.v5.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002276) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Teachey) | Apr 24, 2025 |
| Kids First: Enchondromatoses | [phs001987.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001987.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Sobreira) | Mar 11, 2025 |
| Kids First: Bladder extrophy, Epispadias, Complex | [phs002173.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002173.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Jelin) | Mar 4, 2025 |
| Children’s Brain Tumor Network (CBTN) | [phs002517.v4.p2](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002517.v4.p2) | [Project](https://www.cbtn.org) | Oct 16, 2024 |
| Kids First: Cornelia de Lange Syndrome | [phs002174.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002174.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Krantz) | Aug 2, 2024 |
| Kids First: Ewing Sarcoma – Genetic Risk | [phs001228.v3.p2](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001228) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Schiffman) | Feb 3, 2024 |
| Kids First: Chromosome 18 Structural Birth Defects | [phs002627.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002627.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2021X01projects#FY21_Cody) | Nov 29, 2023 |
| Kids First: Recessive Structural Brain Defects | [phs002590.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002590.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Gleeson_brain) | Oct 23, 2023 |
| Kids First: Esophageal Atresia and Tracheoesophageal Fistulas | [phs002161.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002161.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Chung) | Aug 23, 2023 |
| Kids First: Leukemia & Heart Defects in Down Syndrome | [phs002330.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002330.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Lupo) | Aug 11, 2023 |
| Kids First: Structural Defects of The Neural Tube | [phs002591.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002591.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Gleeson) | Aug 7, 2023 |
| Kids First: Kidney and Urinary Tract Defects | [phs002162.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002162.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Gharavi) | Jul 17, 2023 |
| Kids First: Intracranial Germ Cell Tumors | [phs002322.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002322.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Lau) | Jun 6, 2023 |
| Kids First: Fetal Alcohol Spectrum Disorders | [phs002594.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002594.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Chambers) | May 15, 2023 |
| Kids First: Orofacial Clefts – Philippines | [phs002595.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002595.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Leslie) | May 9, 2023 |
| Kids First: CHARGE Syndrome | [phs002592.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002592.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Martin) | Apr 27, 2023 |
| Kids First: Laterality Birth Defects | [phs002589.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002589.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2019X01projects#FY19_Ware) | Apr 12, 2023 |
| Kids First: Adolescent Idiopathic Scoliosis | [phs001410.v2.p2](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001410) | [Project](https://commonfund.nih.gov/kidsfirst/2016x01projects/#Rios16) | Apr 6, 2023 |
| Kids First: Myeloid Malignancies | [phs002187.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002187.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_Meshinchi) | Sep 23, 2021 |
| Kids First: Congenital Heart Defects | [phs001138.v5.p3](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001138) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Seidman) | Sep 21, 2021 |
| Kids First: Microtia – Hispanic | [phs002172.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002172) | [Project](https://commonfund.nih.gov/kidsfirst/2018X01projects#FY18_J.Seidman) | Sep 3, 2021 |
| Kid First: Hemangiomas (PHACE) | [phs001785.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001785.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Siegel17) | Aug 23, 2021 |
| Kids First: Nonsyndromic Craniosynostosis | [phs001806.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001806.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Boyd) | Aug 23, 2021 |
| Kids First: Intersections of Cancer & SBD | [phs001846.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001846.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Hakon) | Jun 10, 2021 |
| Kids First: Orofacial Cleft – European Ancestry | [phs001168.v2.p2](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001168) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Marazita) | Apr 9, 2021 |
| Kids First: Craniofacial Microsomia | [phs002130.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002130.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Luquetti) | Nov 18, 2020 |
| Kids First: Osteosarcoma | [phs001714.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001714.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Onel) | Aug 24, 2020 |
| Kids First: Novel Cancer Susceptibility in Families (from BASIC3) | [phs001878.v2.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001878.v2.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2016x01projects/#Plon16) | Jul 21, 2020 |
| Kids First: Orofacial Cleft – African and Asian Ancestry | [phs001997.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001997.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2017X01projects#Azeez) | Jun 23, 2020 |
| Kids First: Familial Leukemia | [phs001738.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001738.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2016x01projects/#Mullighan16) | Jun 17, 2020 |
| Kids First: Neuroblastoma | [phs001436.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001436.v1.p1) | [Project](https://commonfund.nih.gov/kidsfirst/2016x01projects/#Maris16) | Sep 25, 2019 |
| Kids First: Orofacial Cleft – Latin American | [phs001420.v2.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001420) | [Project](https://commonfund.nih.gov/kidsfirst/2016x01projects/#Marazita16) | Jun 27, 2019 |
| Kids First: Disorders of Sex Development | [phs001178.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001178) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Vilain) | May 28, 2019 |
| Kids First: Syndromic Cranial Dysinnervation | [phs001247.v1.p1](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001247) | [Project](https://commonfund.nih.gov/kidsfirst/2015X01projects#Engle) | May 28, 2019 |

The study files also retain inclusion/exclusion criteria, selected publications, disease terms and attribution where present. Empty catalogue fields remain empty; they are not evidence of absence. Portal release dates and dbGaP version identifiers are different fields and are not treated as interchangeable.
