# data-sheets-schema

A LinkML schema for Datasheets for Datasets model as published in [Datasheets for Datasets](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext). Inspired by datasheets as used in the electronics and other industries, Gebru et al. proposed that every dataset "be accompanied with a datasheet that documents its motivation, composition, collection process, recommended uses, and so on". To this end the authors create a series of topics and over 50 questions addressing different aspects of datasets, also useful in an AI/ML context. An example of completed datasheet for datasets can be found here:
[Structured dataset documentation: a datasheet for CheXpert](https://arxiv.org/abs/2105.03020)

Google is working with a different model called [Data Cards](https://arxiv.org/abs/2204.01075), which in practice is close to the original Datasheets for Datasets template.

This repository stores a LinkML schema representation for the original Datasheets for Datasets model, representing the topics, sets of questions, and expected entities and fields in the answers (work in progress). Beyond a less structured markdown template for this model (e.g. [template for datasheet for dataset](https://github.com/fau-masters-collected-works-cgarbin/datasheet-for-dataset-template)) we are not aware of any other structured form representing Datasheets for Datasets.

We are also tracking related developments, such as augmented Datasheets for Datasets models as in [Augmented Datasheets for Speech Datasets and Ethical Decision-Making](https://dl.acm.org/doi/10.1145/3593013.3594049).

## Repository Structure

* [examples/](examples/) - example data
* [project/](project/) - project files (do not edit these)
* [src/](src/) - source files (edit these)
  * [data_sheets_schema](src/data_sheets_schema)
    * [schema](src/data_sheets_schema/schema) -- LinkML schema
      (edit this)
    * [datamodel](src/data_sheets_schema/datamodel) -- generated
      Python datamodel
* [tests/](tests/) - Python tests

## Developer Documentation

<details>
Use the `make` command to generate project artefacts:

* `make all`: make everything
* `make deploy`: deploys site
</details>

## Credits

This project was made with
[linkml-project-cookiecutter](https://github.com/linkml/linkml-project-cookiecutter).
