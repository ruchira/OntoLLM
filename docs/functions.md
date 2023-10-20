# OntoGPT Functions

All OntoGPT functions are run from the command line.

Precede all commands with `ontogpt`.

To see the full list of available commands, run this:

```bash
ontogpt --help
```

## Basic Parameters

To see verbose output, run:

```bash
ontogpt -v
```

The options `-vv` and `-vvv` will enable progressively more verbose output.

### cache-db

Use the option `--cache-db` to specify a path to a sqlite database to cache the prompt-completion results.

### skip-annotator

Use the option `--skip-annotator` to skip one or more annotators (e.g. `--skip-annotator gilda`).

## Common Parameters

The following options are available for most functions unless stated otherwise.

### inputfile

Use the option `--inputfile` to specify a path to a file containing input text.

### template

Use the option `--template` to specify a template to use. This is a required parameter.

Only the name is required, without any filename suffix.

To use the `gocam` template, for example, the parameter will be `--template gocam`

This may be one of the templates included with OntoGPT or a custom template, but in the latter case, the schema, generated Pydantic classes, and any imported schemas should be present in the same location.

### target-class

Use the option `--target-class` to specify a class in a schema to treat as the root.

If a schema does not already specify a root class, this is required.

Alternatively, the target class can be specified as part of the `--template` option, like so: `--template mendelian_disease.MendelianDisease`

### model

Use the option `model` to specify the name of a large language model to be used.

For example, this may be `--model gpt-4`.

Consult the full list of available models with:

```bash
ontogpt list-models
```

### recurse

Use the option `recurse` to specify whether recursion should be used when parsing the schema.

Recursion is on by default.

Disable it with `--no-recurse`.

### use-textract

Use the option `use-textract` to specify whether to use the [textract](https://textract.readthedocs.io/en/stable/) package to extract text from the input document. Textract supports retrieving raw text from PDFs, images, audio, and a variety of other formats.

Textract extraction is off by default.

Enable it with `--use-textract`.

### output

Use the option `output` to provide a path to write an output file to.

If this path is not provided, OntoGPT will write to stdout.

### output-format

Use the option `output-format` to specify the desired output file format.

This may be one of:

* html
* json
* jsonl
* md
* owl
* pickle
* turtle
* yaml

### auto-prefix

Use the option `auto-prefix` to define a prefix to use for entities without a matching namespace.

When OntoGPT's extract functions find an entity matching the input schema but cannot ground it, the entity will still be included in the output.

By default, these entities will be assigned identifiers like `AUTO:tangerine`. If you ground this term to the [Food Ontology](https://foodon.org), however, the entity may be `FOODON:00003488` instead.

### show-prompt

Use the option `show-prompt` to show _all_ prompts constructed and sent to the model. Otherwise, only the final prompt will be shown.

Showing the full prompt is off by default.

Enable it by using `--show-prompt` and setting the verbosity level to high (`-vvv`).

## Functions

### categorize-mappings

Categorize a collection of mappings in the Simple Standard for Sharing Ontological Mappings (SSSOM) format.

Mappings in this format may not include their specific mapping types (e.g., broad or close mappings).

This function will attempt to apply more specific mappings wherever possible.

Example:

Using an [example SSSOM mapping collection](https://github.com/mapping-commons/sssom/blob/master/examples/embedded/mp-hp-exact-0.0.1.sssom.tsv)

```bash
ontogpt categorize-mappings -i mp-hp-exact-0.0.1.sssom.tsv
```

Note that OntoGPT will attempt to retrieve the resources specified in the mapping (in the above example, that will include HP and MP). If it cannot find a corresponding resource it will raise a HTTP 404 error.

### clinical-notes

Create mock clinical notes.

Options:

* `-d`, `--description TEXT` - a text description of the contents of the generated notes.
* `--sections TEXT` - sections to include in the generated notes, for example, medications, vital signs. Use multiple times for multiple sections, e.g., `--sections medications --sections "vital signs"`

Example:

```bash
ontogpt clinical-notes -d "middle-aged female patient with syncope and recent travel to the Amazon rainforest"
```

### complete

Prompt completion.

Given the path to a file containing text to continue, this command will simply pass it to the model as a completion task.

Example:

The file `example2.txt` contains the text "Here's a good joke about high blood pressure:"

```bash
ontogpt complete example2.txt
```

We take no responsibility for joke quality or lack thereof.

### convert

Convert output format.

Rather than a direct format translation, this function performs a full SPIRES extraction on the input file and writes the output in the specified format.

Example:

```bash
ontogpt convert -o outputfile.md -O md inputfile.yaml
```

### convert-examples

Convert training examples from YAML.

This can be necessary for performing evaluations.

Given the path to a YAML-format input file containing training examples in a format like this:

```yaml
---
examples:
    - prompt: <text prompt>
      completion: <text of completion of the prompt>
    - prompt: <another text prompt>
      completion: <text of completion of another prompt>
```

the function will convert it to equivalent JSON.

Example:

```bash
ontogpt convert-examples inputfile.yaml
```

### convert-geneset

Convert gene set to YAML.

The gene set may be in JSON (msigdb format) or text (one gene symbol per line) format.

See also the `create-gene-set` command (see below).

Options:

* `--fill` / `--no-fill` - Defaults to False (`--no-fill`). If True (`--fill`), the function will attempt to fill in missing gene values.
* `-U`, `--input-file TEXT` - Path to a file with gene IDs to enrich (if not passed as arguments).

Example:

```bash
ontogpt convert-geneset -U inputfile.json
```

### create-gene-set

Create a gene set.

This is primarily relevant to the TALISMAN method for creating gene set summaries.

It creates a gene set given a set of gene annotations in two-column TSV or GAF format.

The function also requires a single argument for the term to create the gene set with.

The output is provided in YAML format.

Options:

* `-A`, `--annotation-path TEXT` - Path to a file containing annotations.

Example:

```bash
ontogpt create-gene-set -A inputfile.tsv "positive regulation of mitotic cytokinesis"
```

### diagnose

Diagnose a clinical case represented as one or more [Phenopackets](http://phenopackets.org/).

This function takes one or more file paths as arguments, where each must contain a phenopacket in JSON format.

Example inputs may be found at the [Phenomics Exchange repository](https://github.com/phenopackets/phenomics-exchange-ig).

Example:

```bash
ontogpt diagnose case1.json case2.json 
```

### dump-completions

Dump cached completions.

OntoGPT saves queries and successful text completions to an sqlite database.

Caching is not currently supported for local models.

Use this function to retrieve the contents of this database.

See also: the `cache-db` parameter described above.

Options:

* `-m TEXT` - Match string to use for filtering.
* `-D TEXT` - Path to sqlite database.

Example:

```bash
ontogpt dump-completions -m "soup"
```

### embed

Embed text.

This function will return an embedding vector for the input text or texts.

Embedding retrieval is not currently supported for local models.

Options:

* `-C`, `--context TEXT` - domain e.g. anatomy, industry, health-related

Example:

```bash
ontogpt embed "obstreperous muskrat"
```

For OpenAI's "text-embedding-ada-002" model, the output will be a vector of length 1536, like so:

```bash
[-0.015013165771961212, -0.013102399185299873, -0.005333086010068655, ...]
```

### enrichment

Gene class summary enriching. This is OntoGPT's implementation of TALISMAN.

The goal of gene summary enrichment is to assemble a textual summary of the functions of a set of genes and their products.

TALISMAN can run in three different ways:

1. Map gene symbols to IDs using the resolver (unless IDs are specified)
2. Fetch gene descriptions using Alliance API
3. Create a prompt using descriptions

Options:

* `-r`, `--resolver TEXT` - OAK selector for the gene ID resolver, e.g., `sqlite:obo:hgnc` for HGNC gene IDs.
* `-C`, `--context TEXT` - domain, e.g., anatomy, industry, health-related
* `--strict` / `--no-strict` - If set, there must be a unique mappings from labels to IDs. Defaults to True.
* `-U`, `--input-file TEXT` - Path to a file with gene IDs to enrich if not passed as arguments.
* `--randomize-gene-descriptions-using-file TEXT` - For evaluation only. Path to a file containing gene identifiers and descriptions; if this option is used, TALISMAN will swap out gene descriptions with those from this gene set file.
* `--ontological-synopsis` / `--no-ontological-synopsis` - If set, use automated rather than manual gene descriptions. Defaults to True.
* `--combined-synopsis` / `--no-combined-synopsis` - If set, combine gene descriptions. Defaults to False.
* `--end-marker TEXT` - Specify a character or string to end prompts with. For testing minor variants of prompts.
* `--annotations` / `--no-annotations` - If set, include annotations in the prompt. Defaults to True.
* `--prompt-template TEXT` - Path to a file containing the prompt.
* `--interactive` / `--no-interactive` - Interactive mode - rather than call the API, the function will present a walkthrough process. Defaults to False.

Example:

```bash
ontogpt enrichment -r sqlite:obo:hgnc -U tests/input/genesets/EDS.yaml
```

In this case, the prompt will include gene summaries retrieved from the database.

The response text will include, among other fields, a summary like this:

```text
Summary: The common function among these genes is their involvement in the regulation and organization of the extracellular matrix, particularly collagen fibril organization and biosynthesis.
```

### entity-similarity

Determine similarity between ontology entities by comparing their embeddings.

Options:

* `-r`, `--ontology TEXT` - name of the ontology to use. This should be an OAK adapter name such as "sqlite:obo:hp".
* `--definitions` / `--no-definitions` - Include text definitions in the text to embed. Defaults to True.
* `--parents` / `--no-parents` - Include is-a parent terms in the text to embed. Defaults to True.
* `--ancestors` / `--no-ancestors` - Include all ancestors in the text to embed. Defaults to True.
* `--logical-definitions` / `--no-logical-definitions`- Include logical definitions in the text to embed. Defaults to True.
* `--autolabel` / `--no-autolabel` - Add labels to each subject and object identifier. Defaults to True.
* `--synonyms` / `--no-synonyms` - Include synonyms in the text to embed. Defaults to True.

Example:

```bash
ontogpt entity-similarity -r sqlite:obo:hp HP:0012228 HP:0000629
```

In this case, the output will look like this:

```text
subject_id      subject_label   object_id       object_label    embedding_cosine_similarity     object_rank_for_subject
HP:0012228      Tension-type headache   HP:0012228      Tension-type headache   0.9999999999999999      0
HP:0012228      Tension-type headache   HP:0000629      Periorbital fullness    0.7755551231762359      1
HP:0000629      Periorbital fullness    HP:0000629      Periorbital fullness    1.0000000000000002      0
HP:0000629      Periorbital fullness    HP:0012228      Tension-type headache   0.7755551231762359      1
```

### eval

Evaluate an extractor.

See the Evaluations section for more details.

Options:

* `--num-tests INTEGER` - number of test iterations to cycle through. Defaults to 5.

Example:

```bash
ontogpt eval --num-tests 1 EvalCTD
```

### eval-enrichment

Run enrichment (TALISMAN) using multiple methods.

This function runs a set of evaluations specific to the TALISMAN gene set summary process.

It will iterate through all relevant models to compare results.

The function assumes genes will have HGNC identifiers.

Options:

* `--strict` / `--no-strict` - If set, there must be a unique mappings from labels to IDs. Defaults to True.
* `-U`, `--input-file TEXT` - Path to a file with gene IDs to enrich (if not passed as arguments)
* `--ontological-synopsis` / `--no-ontological-synopsis` - If set, use automated rather than manual gene descriptions. Defaults to True.
* `--combined-synopsis` / `--no-combined-synopsis` - If set, combine gene descriptions. Defaults to False.
* `--annotations` / `--no-annotations` - If set, include annotations in the prompt. Defaults to True.
* `-n`, `--number-to-drop INTEGER` - Maximum number of genes to drop if necessary.
* `-A`, `--annotations-path TEXT` - Path to file containing annotations.

Example:

```bash
ontogpt enrichment -U tests/input/genesets/EDS.yaml
```

### extract

Extract knowledge from text guided by a schema.

This is OntoGPT's implementation of SPIRES.

Output includes the input text (or a truncated part), the raw completion output, the prompt (specifically, the last iteration of the prompts used), and an extracted object containing all parts identified in the input text, as well as a list of named entities and their labels.

Options:

* `-S`, `--set-slot-value TEXT` - Set slot value manually, e.g., `--set-slot-value has_participant=protein`

Examples:

```bash
ontogpt extract -t gocam.GoCamAnnotations -i tests/input/cases/gocam-33246504.txt
```

In this case, you will an extracted object in the output like:

```yaml
extracted_object:
  genes:
    - HGNC:5992
    - AUTO:F4/80
    - HGNC:16400
    - HGNC:1499
    - HGNC:5992
    - HGNC:5993
  organisms:
    - NCBITaxon:10088
    - AUTO:bone%20marrow-derived%20macrophages
    - AUTO:astrocytes
    - AUTO:bipolar%20cells
    - AUTO:vascular%20cells
    - AUTO:perivascular%20MPs
  gene_organisms:
    - gene: HGNC:5992
      organism: AUTO:mononuclear%20phagocytes
    - gene: HGNC:16400
      organism: AUTO:F4/80%2B%20mononuclear%20phagocytes
    - gene: HGNC:1499
      organism: AUTO:F4/80%2B%20mononuclear%20phagocytes
    - gene: HGNC:5992
      organism: AUTO:perivascular%20macrophages
    - gene: HGNC:5993
      organism: AUTO:None
  activities:
    - GO:0006954
    - AUTO:photoreceptor%20death
    - AUTO:retinal%20function
  gene_functions:
    - gene: HGNC:5992
      molecular_activity: GO:0006954
    - gene: AUTO:F4/80
      molecular_activity: AUTO:mononuclear%20phagocyte%20recruitment
    - gene: HGNC:1499
      molecular_activity: GO:0006954
    - gene: HGNC:5992
      molecular_activity: AUTO:immune-specific%20expression
    - gene: HGNC:5993
      molecular_activity: AUTO:IL-1%CE%B2%20receptor
    - gene: AUTO:rytvela
      molecular_activity: AUTO:IL-1R%20modulation
    - gene: AUTO:Kineret
      molecular_activity: AUTO:IL-1R%20antagonism
  cellular_processes:
    - AUTO:macrophage-induced%20photoreceptor%20death
  gene_localizations:
    - gene: HGNC:5992
      location: AUTO:subretinal%20space
```

Or, we can extract information about a drug and specify which model to use:

```bash
ontogpt extract -t drug -i tests/input/cases/drug-DB00316-moa.txt --auto-prefix UNKNOWN -m gpt-4
```

The `ontology_class` schema may be used to perform more domain-agnostic entity recognition, though this is generally incompatible with grounding.

```bash
ontogpt extract -t ontology_class -i tests/input/cases/human_urban_green_space.txt
```

### fill

Fill in missing values.

Requires the path to a file containing a data object to be passed (as an argument) and a set of examples as an input file.

Options:

* `-E`, `--examples FILENAME` - Path to a file of example objects.

### generate-extract

Generate text and then extract knowledge from it.

This command runs two operations:

1. Generate a natural language description of something
2. Parse the generated description using SPIRES

For example, given a cell type such as [Acinar Cell Of Salivary Gland](https://cellxgene.cziscience.com/cellguide/CL_0002623), generate a description using GPT describing many aspects of the cell type, from its marker genes through to its function and diseases it is implicated in.

After that, use the [cell-type schema](https://w3id.org/ontogpt/cell_type) to extract this into structured form.

As an optional next step use [linkml-owl](https://github.com/linkml/linkml-owl) to generate OWL TBox axioms.

See also: `iteratively-generate-extract` below.

Example:

```bash
ontogpt generate-extract -t cell_type CL:0002623
```

### iteratively-generate-extract

Iterate through generate-extract.

This runs the `generate-extract` command in iterative mode. It will traverse the extracted subtypes with each iteration, gradually building up an ontology that is entirely generated from the "latent knowledge" in the LLM.

Currently each iteration is independent so the method remains unaware as to whether it has already made a concept. Ungrounded concepts may indicate gaps in available knowledgebases.

Unlike the `generate-extract` command, this command requires some additional parameters to be specified.

Please specify the input ontology and the output path.

Options:

* `-r`, `--ontology TEXT` - Ontology to use. Use the OAK selector format, e.g., "sqlite:obo:cl"
* `-M`, `--max-iterations INTEGER` - Maximum number of iterations.
* `-I`, `--iteration-slot TEXT` - Slots to iterate over.
* `-D`, `--db TEXT` - Path to the output, in YAML format.
* `--clear` / `--no-clear` - If set, clear the output database before starting. Defaults to False.

Example:

```bash
ontogpt iteratively-generate-extract -t cell_type -r sqlite:obo:cl -D cells.yaml CL:0002623 
```

### list-models

List all available models.

Example:

```bash
ontogpt list-models
```

### list-templates

List the templates.

Alternatively, run `make list_templates`.

Example:

```bash
ontogpt list-templates
```

### pubmed-annotate

Retrieve a collection of PubMed IDs for a given search, then perform extraction on them with SPIRES.

The search argument will accept all parameters known to PubMed search, such as filtering by publication year.

Works for single publications, too - set the `--limit` parameter to 1 and specify a PubMed ID as the search argument.

Options:

* `--limit INTEGER` - Total number of citation records to return. Limited by the NCBI API.
* `--get-pmc` / `--no-get-pmc` - Attempt to parse PubMed Central full text(s) rather than abstract(s) alone.

Examples:

```bash
ontogpt pubmed-annotate -t phenotype "Takotsubo Cardiomyopathy: A Brief Review" --get-pmc --model gpt-3.5-turbo-16k --limit 3
```

```bash
ontogpt pubmed-annotate -t environmental_sample "33126925" --limit 1
```

```bash
ontogpt pubmed-annotate -t composite_disease "(earplugs) AND (("1950"[Date - Publication] : "1990"[Date - Publication]))" --limit 4
```

### pubmed-extract

Extract knowledge from a single PubMed ID.

_DEPRECATED_ - use `pubmed-annotate` instead.

### recipe-extract

Extract from a recipe on the web.

This uses the `recipe` template and the [recipe_scrapers](https://github.com/hhursev/recipe-scrapers) package. The latter supports many different recipe web sites, so give your favorite a try.

Pass a URL as the argument, or use the -R option to specify the path to a file containing one URL per line.

Options:

* `-R`, `--recipes-urls-file TEXT` - File with URLs to recipes to use for extraction.

Example:

```bash
ontogpt recipe-extract https://www.allrecipes.com/recipe/17445/grilled-asparagus/
```

In this case, expect an extracted object like the following:

```yaml
extracted_object:
  url: https://www.allrecipes.com/recipe/17445/grilled-asparagus/
  label: Grilled Asparagus
  description: Grilled asparagus with olive oil, salt, and pepper.
  categories:
    - AUTO:None
  ingredients:
    - food_item:
        food: FOODON:03311349
        state: fresh, spears
      amount:
        value: '1'
        unit: UO:0010034
    - food_item:
        food: FOODON:03301826
      amount:
        value: '1'
        unit: UO:0010042
    - food_item:
        food: AUTO:salt
        state: and pepper
      amount:
        value: N/A
        unit: AUTO:N/A
  steps:
    - action: AUTO:Preheat
      inputs:
        - food: AUTO:outdoor%20grill
          state: None
      outputs:
        - food: AUTO:None
          state: None
      utensils:
        - AUTO:None
    - action: dbpediaont:season
      inputs:
        - food: FOODON:00003458
          state: coated
        - food: AUTO:salt
          state: None
        - food: FOODON:00003520
      outputs:
        - food: FOODON:00003458
          state: seasoned
      utensils:
        - AUTO:None
    - action: AUTO:cook
      inputs:
        - food: FOODON:03311349
          state: None
      outputs:
        - food: FOODON:03311349
          state: cooked
      utensils:
        - AUTO:grill
```

### synonyms

Extract synonyms, based on embeddings.

The context parameter is required.

Options:

* `-C`, `--context TEXT` - domain, e.g., anatomy, industry, health-related

Example:

```bash
ontogpt synonyms --context astronomy star
```

### text-distance

Embed text and calculate euclidian distance between the embeddings.

The terms must be separated by an `@` character.

Options:

* `-C`, `--context TEXT` - domain, e.g., anatomy, industry, health-related

Example:

```bash
ontogpt text-distance pancakes @ syrup
```

### text-similarity

Like `text-distance`, this command compares the embeddings of input terms.

This command returns the cosine similarity of the embedding vectors.

Options:

* `-C`, `--context TEXT` - domain, e.g., anatomy, industry, health-related

Example:

```bash
ontogpt text-similarity basketball @ basket-weaving
```

### web-extract

Extract knowledge from web page.

Pass a URL as an argument and OntoGPT will use the SPIRES method to extract information based on the specified template.

Because this depends upon scraping a page, results may vary depending on a site's complexity and structure.

Even relatively short pages may exceed a model's context size, so larger context models may be necessary.

Example:

```bash
ontogpt web-extract -t reaction.Reaction -m gpt-3.5-turbo-16k https://www.scienceofcooking.com/maillard_reaction.htm 
```

### wikipedia-extract

Extract knowledge from a Wikipedia page.

Pass an article title as an argument and OntoGPT will use the SPIRES method to extract information based on the specified template.

Even relatively short pages may exceed a model's context size, so larger context models may be necessary.

Example:

```bash
ontogpt wikipedia-extract -t mendelian_disease.MendelianDisease -m gpt-3.5-turbo-16k "Cartilage–hair hypoplasia"
```

### wikipedia-search

Extract knowledge from Wikipedia pages based on a search.

Pass a search phrase as an argument and OntoGPT will use the SPIRES method to extract information based on the specified template.

Even relatively short pages may exceed a model's context size, so larger context models may be necessary.

Example:

```bash
ontogpt wikipedia-search -t biological_process -m gpt-3.5-turbo-16k "digestion"
```
