# OntoLLM

OntoLLM is a descendant of [OntoGPT](https://github.com/monarch-initiative/ontogpt). While OntoGPT requires an account with "OpenAI" in order to run, OntoLLM supports LLMs that are open source and available for commercial use. A number of open-source LLMs, with [varying degrees of actual openness](https://opening-up-chatgpt.github.io), are available today. OntoLLM seeks to remove the pre-requisite "OpenAI account" from OntoGPT, and provide a modified set of instructions, for users planning to use a different LLM.

## Tracking the upstream git repository

OntoLLM is closely tracking the upstream OntoGPT repository, though with
slight differences as described above. [More technical
details](DivergenceFromUpstream.md) are available about how we track upstream
commits while maintaining independence from OpenAI.

## Original README

The original README from the OntoGPT project is currently below.

___

[![DOI](https://zenodo.org/badge/13996/monarch-initiative/ontogpt.svg)](https://zenodo.org/badge/latestdoi/13996/monarch-initiative/ontogpt)
![PyPI](https://img.shields.io/pypi/v/ontogpt)

## Introduction

OntoGPT is a Python package for generating ontologies and knowledge bases using large language models (LLMs). It makes use of so-called *instruction prompts* in LLMs such as GPT-4.

Two different strategies for knowledge extraction are currently implemented in OntoGPT:

* SPIRES: *Structured Prompt Interrogation and Recursive Extraction of Semantics*
  * A Zero-shot learning (ZSL) approach to extracting nested semantic structures from text
  * This approach takes two inputs - 1) LinkML schema 2) free text, and outputs knowledge in a structure conformant with the supplied schema in JSON, YAML, RDF or OWL formats
  * Uses GPT-3.5-turbo, GPT-4, or one of a variety of open LLMs on your local machine
* SPINDOCTOR: *Structured Prompt Interpolation of Narrative Descriptions Or Controlled Terms for Ontological Reporting*
  * Summarizes gene set descriptions (pseudo gene-set enrichment)
  * Uses GPT-3.5-turbo or GPT-4

## Prerequisites for running OntoGPT

* Python 3.9+

* OpenAI API key: necessary for using OpenAI's GPT models. This is a paid API and you will be charged based on usage. If you do not have an OpenAI account, [you may sign up here](https://platform.openai.com/signup). You will need to set your API key using the [Ontology Access Kit](https://github.com/INCATools/ontology-access-kit):

```bash
poetry run runoak set-apikey -e openai <your openai api key>
```

You may also set additional API keys for optional resources:

* [BioPortal](https://bioportal.bioontology.org/) account (for grounding). The BioPortal key is necessary for using ontologies from [BioPortal](https://bioportal.bioontology.org/). You may get a key by signing up for an account on their web site.
* [NCBI E-utilities](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/). The NCBI email address and API key are used for retrieving text and metadata from PubMed. You may still access these resources without identifying yourself, but you may encounter rate limiting and errors.
* [HuggingFace Hub](https://huggingface.co/docs/api-inference/quicktour#get-your-api-token). This API key is necessary to retrieve models from the HuggingFace Hub service.

These optional keys may be set as follows:

```bash
poetry run runoak set-apikey -e bioportal <your bioportal api key>
poetry run runoak set-apikey -e ncbi-email <your email address>
poetry run runoak set-apikey -e ncbi-key <your NCBI api key>
poetry run runoak set-apikey -e hfhub-key <your HuggingFace Hub api key>
```

## Setup

To simply start using the package in your workspace:

```bash
pip install ontogpt
```

Note that some features require installing additional, optional dependencies.

These may be installed as:

```bash
poetry install --extras extra_name
# OR
pip install ontogpt[extra_name]
```

where `extra_name` is one of the following:

* `docs` - dependencies for building documentation
* `web` - dependencies for the web application
* `recipes` - dependencies for recipe scraping and parsing
* `huggingface` - dependencies for accessing LLMs from HuggingFace Hub, remotely or locally

For feature development and contributing to the package:

```bash
git clone https://github.com/monarch-initiative/ontogpt.git
cd ~/path/to/ontogpt
poetry install
```

## Getting Started

OntoGPT is run from the command line. See the full list of commands with:

```bash
ontogpt --help
```

For a simple example of text completion and testing to ensure OntoGPT is set up correctly, create a text file containing the following, saving the file as `example.txt`:

```
Why did the squid cross the coral reef?
```

Then try the following command:

```bash
ontogpt complete example.txt
```

You should get text output like the following:

```
Perhaps the squid crossed the coral reef for a variety of reasons:

1. Food: Squids are known to feed on small fish and other marine organisms, and there could have been a rich food source on the other side of the reef.

...
```

OntoGPT is intended to be used for information extraction. The following examples show how to accomplish this.

### Strategy 1: Knowledge extraction using SPIRES

#### Working Mechanism

1. You provide an arbitrary data model, describing the structure you want to extract text into. This can be nested (but see limitations below). The predefined [templates](src/ontogpt/templates/) may be used.
2. Provide your preferred annotations for grounding `NamedEntity` fields
3. OntoGPT will:
    - Generate a prompt
    - Feed the prompt to a language model
    - Parse the results into a dictionary structure
    - Ground the results using a preferred annotator (e.g., an ontology)

#### Input

Consider some text from one of the input files being used in the OntoGPT test suite. You can find the text file [here](tests/input/cases/gocam-betacat.txt). You can download the raw file from the GitHub link to that input text file, or copy its contents over into another file, say, `abstract.txt`. An excerpt:

  > The cGAS/STING-mediated DNA-sensing signaling pathway is crucial
  for interferon (IFN) production and host antiviral
  responses
  > 
  > ...
  > [snip] 
  > ...
  > 
  > The underlying mechanism was the
  interaction of US3 with β-catenin and its hyperphosphorylation of
  β-catenin at Thr556 to block its nuclear translocation
  > ...
  > ...

We can extract knowledge from the above text this into the [GO pathway datamodel](src/ontogpt/templates/gocam.yaml) by running the following command:

#### Command

```bash
ontogpt extract -t gocam.GoCamAnnotations -i ~/path/to/abstract.txt
```

Note: The value accepted by the `-t` / `--template` argument is the base name of one of the LinkML schema / data model which can be found in the [templates](src/ontogpt/templates/) folder.

#### Output

The output returned from the above command can be optionally redirected into an output file using the `-o` / `--output`.

The following is a small part of what the larger schema-compliant output looks like:

```yaml
genes:
- HGNC:2514
- HGNC:21367
- HGNC:27962
- US3
- FPLX:Interferon
- ISG
gene_gene_interactions:
- gene1: US3
  gene2: HGNC:2514
gene_localizations:
- gene: HGNC:2514
  location: Nuclear
gene_functions:
- gene: HGNC:2514
  molecular_activity: Transcription
- gene: HGNC:21367
  molecular_activity: Production
...
```

#### Local Models

To use a local model, specify it with the `-m` or `--model` option.

Example:

```bash
ontogpt extract -t drug -i ~/path/to/abstract.txt -m nous-hermes-13b
```

See the list of all available models with this command:
```bash
ontogpt list-models
```

When specifying a local model for the first time, it will be downloaded to your local system.

## Strategy 2: Gene Enrichment using SPINDOCTOR

Given a set of genes, OntoGPT can find similarities among them.

Ex.:

```bash
ontogpt enrichment -U tests/input/genesets/sensory-ataxia.yaml
```

The default is to use ontological gene function synopses (via the Alliance API).

* To use narrative/RefSeq summaries, use the `--no-ontological-synopses` flag
* To run without any gene descriptions, use the `--no-annotations` flag

This strategy does not currently support using local models.

## Features

### Define your own extraction model using LinkML

There are a number of pre-defined LinkML data models already developed here - [src/ontogpt/templates/](src/ontogpt/templates/) which you can use as reference when creating your own data models.

Define a schema (using a subset of [LinkML](https://linkml.io)) that describes the structure in which you want to extract knowledge from your text.

<details>
  <summary>Open to see an example custom linkml data model</summary>
 
  ```yaml
  classes:
    MendelianDisease:
      attributes:
        name:
          description: the name of the disease
          examples:
            - value: peroxisome biogenesis disorder
          identifier: true  ## needed for inlining
        description:
          description: a description of the disease
          examples:
            - value: >-
              Peroxisome biogenesis disorders, Zellweger syndrome spectrum (PBD-ZSS) is a group of autosomal recessive disorders affecting the formation of functional peroxisomes, characterized by sensorineural hearing loss, pigmentary retinal degeneration, multiple organ dysfunction and psychomotor impairment
        synonyms:
          multivalued: true
          examples:
            - value: Zellweger syndrome spectrum
            - value: PBD-ZSS
        subclass_of:
          multivalued: true
          range: MendelianDisease
          examples:
            - value: lysosomal disease
            - value: autosomal recessive disorder
        symptoms:
          range: Symptom
          multivalued: true
          examples:
            - value: sensorineural hearing loss
            - value: pigmentary retinal degeneration
        inheritance:
          range: Inheritance
          examples:
            - value: autosomal recessive
        genes:
          range: Gene
          multivalued: true
          examples:
            - value: PEX1
            - value: PEX2
            - value: PEX3

    Gene:
      is_a: NamedThing
      id_prefixes:
        - HGNC
      annotations:
        annotators: gilda:, bioportal:hgnc-nr

    Symptom:
      is_a: NamedThing
      id_prefixes:
        - HP
      annotations:
        annotators: sqlite:obo:hp

    Inheritance:
      is_a: NamedThing
      annotations:
        annotators: sqlite:obo:hp
```

</details>

* Prompt hints can be specified using the `prompt` annotation (otherwise description is used)
* Multivalued fields are supported
* The default range is string — these are not grounded. Ex.: disease name, synonyms
* Define a class for each `NamedEntity`
* For any `NamedEntity`, you can specify a preferred annotator using the `annotators` annotation

We recommend following an established schema like [BioLink Model](https://github.com/biolink/biolink-model), but you can define your own.

Next step is to compile the schema. For that, you should place the schema YAML in the directory [src/ontogpt/templates/](src/ontogpt/templates/). Then, run the `make` command at the top level. This will compile the schema to Python (Pydantic classes).

Once you have defined your own schema / data model and placed in the correct directory, you can run the `extract` command. 

Ex.:

```bash
ontogpt extract -t mendelian_disease.MendelianDisease -i marfan-wikipedia.txt
```

### Multiple levels of nesting

Currently no more than two levels of nesting are recommended.

If a field has a range which is itself a class and not a primitive, it will attempt to nest.

Ex. the `gocam` schema has an attribute:

```yaml
  attributes:
      ...
      gene_functions:
        description: semicolon-separated list of gene to molecular activity relationships
        multivalued: true
        range: GeneMolecularActivityRelationship
```

The range `GeneMolecularActivityRelationship` has been specified *inline*, so it will nest.

The generated prompt is:

```bash
gene_functions : <semicolon-separated list of gene to molecular activities relationships>
```

The output of this is then passed through further SPIRES iterations.

### Text length limit

LLMs have context sizes limiting the combined length of their inputs and outputs. The text-davinci-003 model, for example, whas a total 4,000 token limit (prompt + completion), while the gpt-3.5-turbo-16k model has a larger context of 16 thousand tokens.

### Schema tips

It helps to have an understanding of the [LinkML](https://linkml.io) schema language, but it should be possible to define your own schemas using the examples in [src/ontogpt/templates](src/ontogpt/templates/) as a guide.

OntoGPT-specific extensions are specified as *annotations*.

You can specify a set of annotators for a field using the `annotators` annotation.

Ex.:

```yaml
  Gene:
    is_a: NamedThing
    id_prefixes:
      - HGNC
    annotations:
      annotators: gilda:, bioportal:hgnc-nr, obo:pr
```

The annotators are applied in order.

Additionally, when performing grounding, the following measures can be taken to improve accuracy:

* Specify the valid set of ID prefixes using `id_prefixes`
* Some vocabularies have structural IDs that are amenable to regexes, you can specify these using `pattern`
* You can make use of `values_from` slot to specify a [Dynamic Value Set](https://linkml.io/linkml/schemas/enums.html#dynamic-enums)
  * For example, you can constrain the set of valid locations for a gene product to be subclasses of `cellular_component` in GO or `cell` in CL

Ex.:

```yaml
classes:
  ...
  GeneLocation:
    is_a: NamedEntity
    id_prefixes:
      - GO
      - CL
    annotations:
      annotators: "sqlite:obo:go, sqlite:obo:cl"
    slot_usage:
      id:
        values_from:
          - GOCellComponentType
          - CellType

enums:
  GOCellComponentType:
    reachable_from:
      source_ontology: obo:go
      source_nodes:
        - GO:0005575 ## cellular_component
  CellType:
    reachable_from:
      source_ontology: obo:cl
      source_nodes:
        - CL:0000000 ## cell
```

### OWL Exports

The `extract` command will let you export the results as OWL axioms, utilizing [linkml-owl](https://linkml.io/linkml-owl) mappings in the schema.

Ex.:

```bash
ontogpt extract -t recipe -i recipe-spaghetti.txt -o recipe-spaghetti.owl -O owl
```

[src/ontogpt/templates/recipe.yaml](src/ontogpt/templates/recipe.yaml) is an example schema that uses linkml-owl mappings.

See the [Makefile](Makefile) for a full pipeline that involves using robot to extract a subset of FOODON
and merge in the extracted results. This uses [recipe-scrapers](https://github.com/hhursev/recipe-scrapers).

OWL output: [recipe-all-merged.owl](tests/output/owl/merged/recipe-all-merged.owl)

Classification:

<img width="1329" alt="image" src="https://user-images.githubusercontent.com/50745/230427663-20d845e9-f1d5-490e-b1ad-cdccdd0dca70.png">

## Web Application Setup

There is a bare bones web application for running OntoGPT and viewing results.

Install the required dependencies by running the following command:

```bash
poetry install -E web
```

Then run this command to start the web application:

```bash
poetry run web-ontogpt
```

Note: The agent running uvicorn must have the API key set, so for obvious reasons don't host this publicly without authentication, unless you want your credits drained.

### SPINDOCTOR web app

To start:

```bash
poetry run streamlit run src/ontogpt/streamlit/spindoctor.py
```

### HuggingFace Hub

Note: support for HuggingFace-provided models is currently a work in progress.

A select number of LLMs may be accessed through HuggingFace Hub. See the full list using `ontogpt list-models`

Specify a model name with the `-m` option.

Example:

```bash
ontogpt extract -t mendelian_disease.MendelianDisease -i tests/input/cases/mendelian-disease-sly.txt -m FLAN_T5_BASE
```

## Citation

SPIRES is described further in: Caufield JH, Hegde H, Emonet V, Harris NL, Joachimiak MP, Matentzoglu N, et al. Structured prompt interrogation and recursive extraction of semantics (SPIRES): A method for populating knowledge bases using zero-shot learning. arXiv publication: http://arxiv.org/abs/2304.02711

SPINDOCTOR is described further in: Joachimiak MP, Caufield JH, Harris NL, Kim H, Mungall CJ. Gene Set Summarization using Large Language Models. arXiv publication: http://arxiv.org/abs/2305.13338

## Contributing

Contributions on recipes to test welcome from anyone! Just make a PR [here](https://github.com/monarch-initiative/ontogpt/blob/main/tests/input/recipe-urls.csv). See [this list](https://github.com/hhursev/recipe-scrapers) for accepted URLs

## Acknowledgements

We gratefully acknowledge [Bosch Research](https://www.bosch.com/research) for their support of this research project.
