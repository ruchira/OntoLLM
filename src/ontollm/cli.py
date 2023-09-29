"""Command line interface for ontollm."""
import codecs
import json
import logging
import pickle
import sys
from copy import copy, deepcopy
from dataclasses import dataclass
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import List, Optional, Union

import click
import jsonlines
import yaml
from oaklib import get_adapter
from oaklib.cli import query_terms_iterator
from oaklib.interfaces import OboGraphInterface
from oaklib.io.streaming_csv_writer import StreamingCsvWriter
from sssom.parsers import parse_sssom_table, to_mapping_set_document
from sssom.util import to_mapping_set_dataframe

import ontollm.ontex.extractor as extractor
from ontollm import DEFAULT_MODEL, DEFAULT_MODEL_DETAILS, MODELS, __version__
from ontollm.clients import HFHubClient
from ontollm.clients.pubmed_client import PubmedClient
from ontollm.clients.soup_client import SoupClient
from ontollm.clients.wikipedia_client import WikipediaClient
from ontollm.engines import create_engine
from ontollm.engines.embedding_similarity_engine import SimilarityEngine
from ontollm.engines.enrichment import EnrichmentEngine
from ontollm.engines.generic_engine import GenericEngine, QuestionCollection
from ontollm.engines.gpt4all_engine import GPT4AllEngine  # type: ignore
from ontollm.engines.halo_engine import HALOEngine  # type: ignore

# from ontollm.engines.hfhub_engine import HFHubEngine
from ontollm.engines.knowledge_engine import KnowledgeEngine
from ontollm.engines.mapping_engine import MappingEngine
from ontollm.engines.pheno_engine import PhenoEngine
from ontollm.engines.reasoner_engine import ReasonerEngine
from ontollm.engines.spires_engine import SPIRESEngine
from ontollm.engines.synonym_engine import SynonymEngine
from ontollm.evaluation.enrichment.eval_enrichment import EvalEnrichment
from ontollm.evaluation.resolver import create_evaluator
from ontollm.io.csv_wrapper import output_parser, write_obj_as_csv
from ontollm.io.html_exporter import HTMLExporter
from ontollm.io.markdown_exporter import MarkdownExporter
from ontollm.utils.gene_set_utils import (
    GeneSet,
    _is_human,
    fill_missing_gene_set_values,
    parse_gene_set,
)
from ontollm.utils.gpt4all_runner import chain_gpt4all_model, set_up_gpt4all_model

__all__ = [
    "main",
]

from ontollm.io.owl_exporter import OWLExporter
from ontollm.io.rdf_exporter import RDFExporter
from ontollm.io.yaml_wrapper import dump_minimal_yaml
from ontollm.templates.core import ExtractionResult


@dataclass
class Settings:
    """Global command line settings."""

    cache_db: Optional[str] = None
    skip_annotators: Optional[List[str]] = None


settings = Settings()


def _as_text_writer(f):
    if isinstance(f, TextIOWrapper):
        return f
    else:
        return codecs.getwriter("utf-8")(f)


def write_extraction(
    results: ExtractionResult,
    output: BytesIO,
    output_format: str = None,
    knowledge_engine: KnowledgeEngine = None,
):
    """Write results of extraction to a given output stream."""
    # Check if this result contains anything writable first
    if results.extracted_object:
        exporter: Union[MarkdownExporter, HTMLExporter, RDFExporter, OWLExporter]

        if output_format not in ["pickle"]:
            output = _as_text_writer(output)

        if output_format == "pickle":
            output.write(pickle.dumps(results))
        elif output_format == "md":
            exporter = MarkdownExporter()
            exporter.export(results, output)
        elif output_format == "html":
            exporter = HTMLExporter(output=output)
            exporter.export(results, output)
        elif output_format == "yaml":
            output.write("---\n")  # type: ignore
            output.write(dump_minimal_yaml(results))  # type: ignore
        elif output_format == "turtle":
            exporter = RDFExporter()
            exporter.export(results, output, knowledge_engine.schemaview)
        elif output_format == "owl":
            exporter = OWLExporter()
            exporter.export(results, output, knowledge_engine.schemaview)
        elif output_format == "kgx":
            # output.write(write_obj_as_csv(results))
            output.write(dump_minimal_yaml(results))  # type: ignore
            with open("output.kgx.tsv") as secondoutput:
                for line in output_parser(obj=results, file=output):
                    secondoutput.write(line)
        else:
            output.write("---\n")  # type: ignore
            output.write(dump_minimal_yaml(results))  # type: ignore


def get_model_by_name(modelname: str):
    """Retrieve a model name and metadata from those available.

    Returns a dict describing the selected model.
    """
    found = False
    for knownmodel in MODELS:
        if modelname in knownmodel["alternative_names"] or modelname == knownmodel["name"]:
            selectmodel = knownmodel
            found = True
            logging.info(
                f"Found model: {selectmodel['name']}, provided by {selectmodel['provider']}."
            )
            if "not_implemented" in selectmodel or "deprecated" in selectmodel:
                logging.error(f"Model {selectmodel['name']} not implemented or is deprecated.")
                raise NotImplementedError
            break
    if not found:
        logging.warning(
            f"""Model name not recognized or not supported yet. Using default, {DEFAULT_MODEL}.
            See all models with `ontogpt list-models`"""
        )
        selectmodel = DEFAULT_MODEL_DETAILS

    return selectmodel


inputfile_option = click.option("-i", "--inputfile", help="Path to a file containing input text.")
template_option = click.option("-t", "--template", required=True, help="Template to use.")
target_class_option = click.option(
    "-T", "--target-class", help="Target class (if not already root)."
)
interactive_option = click.option(
    "--interactive/--no-interactive",
    default=False,
    show_default=True,
    help="Interactive mode - rather than call the LLM API it will prompt you do this.",
)
model_option = click.option(
    "-m",
    "--model",
    help="Model name to use, e.g. orca-mini-7b."
    " See all model names with ontogpt list-models.",
)
prompt_template_option = click.option(
    "--prompt-template", help="Path to a file containing the prompt."
)
recurse_option = click.option(
    "--recurse/--no-recurse", default=True, show_default=True, help="Recursively parse structures."
)
output_option_wb = click.option(
    "-o", "--output", type=click.File(mode="wb"), default=sys.stdout, help="Output file."
)
output_option_txt = click.option(
    "-o", "--output", type=click.File(mode="w"), default=sys.stdout, help="Output file."
)
output_format_options = click.option(
    "-O",
    "--output-format",
    type=click.Choice(["json", "yaml", "pickle", "md", "html", "owl", "turtle", "jsonl"]),
    default="yaml",
    help="Output format.",
)
auto_prefix_option = click.option(
    "--auto-prefix",
    default="AUTO",
    help="Prefix to use for auto-generated classes. Default is AUTO.",
)
show_prompt_option = click.option(
    "--show-prompt/--no-show-prompt",
    default=False,
    show_default=True,
    help="If set, show all prompts passed to model through an API. Use with verbose setting.",
)
max_gen_len_option = click.option(
    "--max-gen-len",
    default=16000,
    type=click.INT,
    help="Maximum length of generated sequences. Default is 16000.",
)
temperature_option = click.option(
    "--temperature",
    default=0.6,
    type=click.FLOAT,
    help="The temperature value for controlling randomness in generation.  Default is 0.6",
)
top_p_option = click.option(
    "--top-p",
    default=0.9,
    type=click.FLOAT,
    help="The top p sampling parameter for controlling diversity in generation. Default is 0.9",
)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@click.option("--cache-db", help="Path to sqlite database to cache prompt-completion results")
@click.option(
    "--skip-annotator",
    multiple=True,
    help="Skip one or more annotators (e.g. --skip-annotator gilda)",
)
@click.version_option(__version__)
def main(verbose: int, quiet: bool, cache_db: str, skip_annotator):
    """CLI for ontollm.

    :param verbose: Verbosity while running.
    :param quiet: Boolean to be quiet or verbose.
    """
    logger = logging.getLogger()
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)
    logger.info(f"Logger {logger.name} set to level {logger.level}")
    if cache_db:
        settings.cache_db = cache_db
    if skip_annotator:
        settings.skip_annotators = list(skip_annotator)


@main.command()
@inputfile_option
@template_option
@target_class_option
@model_option
@recurse_option
@output_option_wb
@click.option("--dictionary")
@output_format_options
@auto_prefix_option
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option(
    "--set-slot-value",
    "-S",
    multiple=True,
    help="Set slot value, e.g. --set-slot-value has_participant=protein",
)
@click.argument("input", required=False)
def extract(
    inputfile,
    template,
    target_class,
    dictionary,
    input,
    output,
    output_format,
    set_slot_value,
    model,
    show_prompt,
    max_gen_len,
    temperature,
    top_p,
    **kwargs,
):
    """Extract knowledge from text guided by schema, using SPIRES engine.

    Example:

        ontollm extract -t gocam.GoCamAnnotations -i gocam-27929086.txt

    The input argument must be either a file path or a string.
    Use the -i/--input-file option followed by the path to the input file if using the former.
    Otherwise, the input is assumed to be a string to be read as input.

    You can also use fragments of existing schemas, use the --target-class option (-T) to
    specify an alternative Container/root class.

    Example:

        ontollm -extract -t gocam.GoCamAnnotations -T GeneOrganismRelationship "the mouse Shh gene"

    """
    logging.info(f"Creating for {template}")

    # TODO Use another default model source
    # Choose model based on input, or use the default
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]
    model_name = selectmodel["alternative_names"][0]

    if not inputfile or inputfile == "-":
        text = sys.stdin.read()
    if inputfile and Path(inputfile).exists():
        logging.info(f"Input file: {inputfile}")
        text = open(inputfile, "r").read()
        logging.info(f"Input text: {text}")
    elif inputfile and not Path(inputfile).exists():
        raise FileNotFoundError(f"Cannot find input file {inputfile}")

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template=template, model=model_name, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.client.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    elif model_source == "HuggingFace Hub":
        raise NotImplementedError("HF Hub support temporarily disabled. Sorry!")
        # hf_repo_name = selectmodel["hf_repo_name"]
        # ke = HFHubEngine(template=template, local_model=hf_repo_name, **kwargs)

    if dictionary:
        ke.load_dictionary(dictionary)
    if target_class:
        target_class_def = ke.schemaview.get_class(target_class)
    else:
        target_class_def = None
    results = ke.extract_from_text(text=text, class_def=target_class_def,
                                   show_prompt=show_prompt,
                                   max_gen_len=max_gen_len,
                                   temperature=temperature,
                                   top_p=top_p)
    if set_slot_value:
        for slot_value in set_slot_value:
            slot, value = slot_value.split("=")
            setattr(results.extracted_object, slot, value)
    write_extraction(results, output, output_format, ke)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@auto_prefix_option
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.argument("entity")
def generate_extract(model, entity, template, output, output_format, show_prompt,
                     max_gen_len, temperature, top_p, **kwargs):
    """Generate text and then extract knowledge from it."""
    logging.info(f"Creating for {template}")

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    logging.debug(f"Input entity: {entity}")
    results = ke.generate_and_extract(entity, show_prompt,
                                      max_gen_len=max_gen_len,
                                      temperature=temperature,
                                      top_p=top_p)
    write_extraction(results, output, output_format, ke)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@auto_prefix_option
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option("--ontology", "-r", help="Ontology to use; use oaklib selector path")
@click.option("--max-iterations", "-M", default=10, type=click.INT)
@click.option("--iteration-slot", "-I", multiple=True, help="Slots to iterate over")
@click.option("--db", "-D", help="Where the resulting yaml database is stored")
@click.option(
    "--clear/--no-clear", default=False, show_default=True, help="Clear the db before starting"
)
@click.argument("entity")
def iteratively_generate_extract(
    model,
    entity,
    template,
    output,
    output_format,
    db,
    iteration_slot,
    max_iterations,
    clear,
    ontology,
    show_prompt,
    i,
    max_gen_len=max_gen_len,
    temperature=temperature,
    top_p=top_p,
    **kwargs,
):
    """Iterate through generate-extract."""
    logging.info(f"Creating for {template}")

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    logging.debug(f"Input entity: {entity}")
    adapter = get_adapter(ontology)
    for results in ke.iteratively_generate_and_extract(
        entity,
        db,
        show_prompt=show_prompt,
        max_gen_len=max_gen_len,
        temperature=temperature,
        top_p=top_p,
        iteration_slots=list(iteration_slot),
        max_iterations=max_iterations,
        adapter=adapter,
        clear=clear,
    ):
        write_extraction(results, output, output_format)


# TODO: combine this command with pubmed_annotate - they are converging
@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option(
    "--get-pmc/--no-get-pmc",
    default=False,
    help="Attempt to parse PubMed Central full text(s) instead of abstract(s) alone.",
)
@click.argument("pmid")
def pubmed_extract(model, pmid, template, output, output_format, get_pmc, show_prompt, **kwargs):
    """Extract knowledge from a single PubMed ID."""
    logging.info(f"Creating for {template}")

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    pmc = PubmedClient()
    if get_pmc:
        logging.info(f"Will try to retrieve PubMed Central text for {pmid}.")
        textlist = pmc.text(pmid, pubmedcental=True)
    else:
        textlist = pmc.text(pmid)
    for text in textlist:
        logging.debug(f"Input text: {text}")
        results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                       max_gen_len=max_gen_len,
                                       temperature=temperature,
                                       top_p=top_p)
        write_extraction(results, output, output_format)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option(
    "--limit",
    default=20,
    help="Total number of citation records to return.",
)
@click.option(
    "--get-pmc/--no-get-pmc",
    default=False,
    help="Attempt to parse PubMed Central full text(s) instead of abstract(s) alone.",
)
@click.argument("search")
def pubmed_annotate(
    model, search, template, output, output_format, limit, get_pmc, show_prompt,
    max_gen_len, temperature, top_p,
    **kwargs
):
    """Retrieve a collection of PubMed IDs for a search term; annotate them using a template.

    Example:
    ontogpt pubmed-annotate -t phenotype "Takotsubo Cardiomyopathy: A Brief Review"
        --get-pmc --model gpt-3.5-turbo-16k --limit 3
    """
    logging.info(f"Creating for {template}")

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    pubmed_annotate_limit = limit
    pmc = PubmedClient()
    pmids = pmc.get_pmids(search)
    if get_pmc:
        logging.info("Will try to retrieve PubMed Central texts.")
        textlist = pmc.text(pmids[: pubmed_annotate_limit + 1], pubmedcental=True)
    else:
        textlist = pmc.text(pmids[: pubmed_annotate_limit + 1])
    for text in textlist:
        logging.debug(f"Input text: {text}")
        results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                       max_gen_len=max_gen_len,
                                       temperature=temperature,
                                       top_p=top_p)
        write_extraction(results, output, output_format, ke)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option("--auto-prefix", default="AUTO", help="Prefix to use for auto-generated classes.")
@click.argument("article")
def wikipedia_extract(model, article, template, output, output_format,
                      show_prompt, max_gen_len, temperature, top_p, **kwargs):
    """Extract knowledge from a Wikipedia page."""
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    logging.info(f"Creating for {template} => {article}")
    client = WikipediaClient()
    text = client.text(article)

    logging.debug(f"Input text: {text}")
    results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                   max_gen_len=max_gen_len,
                                   temperature=temperature,
                                   top_p=top_p)
    write_extraction(results, output, output_format, ke)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option(
    "--keyword",
    "-k",
    multiple=True,
    help="Keyword to search for (e.g. --keyword therapy). Also obtained from schema",
)
@click.argument("topic")
def wikipedia_search(model, topic, keyword, template, output, output_format,
                     show_prompt, max_gen_len, temperature, top_p, **kwargs):
    """Extract knowledge from a Wikipedia page."""
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    logging.info(f"Creating for {template} => {topic}")
    client = WikipediaClient()
    keywords = list(keyword) if keyword else []
    logging.info(f"KW={keywords}")

    keywords.extend(ke.schemaview.schema.keywords)
    search_term = f"{topic + ' ' + ' '.join(keywords)}"
    print(f"Searching for {search_term}")
    search_results = client.search_wikipedia_articles(search_term)
    for _index, result in enumerate(search_results, start=1):
        title = result["title"]
        text = client.text(title)
        logging.debug(f"Input text: {text}")
        if len(text) > 4000:
            # TODO - expand this to fit context limits better
            # or add as cli option
            text = text[:4000]
        results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                       max_gen_len=max_gen_len,
                                       temperature=temperature,
                                       top_p=top_p)
        write_extraction(results, output, output_format)
        break


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.option(
    "--keyword",
    "-k",
    multiple=True,
    help="Keyword to search for (e.g. --keyword therapy). Also obtained from schema",
)
@click.argument("term_tokens", nargs=-1)
def search_and_extract(
    model, term_tokens, keyword, template, output, output_format, show_prompt,
    max_gen_len, temperature, top_p,
    **kwargs
):
    """Search for relevant literature and extract knowledge from it."""
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    term = " ".join(term_tokens)
    logging.info(f"Creating for {template}; search={term} kw={keyword}")

    logging.info(f"Creating PubMed client for {template}; search={term}")
    pmc = PubmedClient()
    logging.info("Got client")
    keywords = list(keyword) if keyword else []
    logging.info(f"KW={keywords}")
    keywords.extend(ke.schemaview.schema.keywords)
    logging.info(f"Keywords={keywords}")
    if not keywords:
        raise ValueError("No keywords specified; use --keyword or annotate schema with keywords")
    pmids = list(pmc.search(term, keywords))
    logging.info(f"PMIDs={pmids}")
    pmid = pmids[0]
    logging.info(f"PMID={pmid}")
    text = pmc.text(pmid)
    logging.info(f"Input text: {text}")
    results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                   max_gen_len=max_gen_len,
                                   temperature=temperature,
                                   top_p=top_p)
    write_extraction(results, output, output_format)


@main.command()
@template_option
@model_option
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.argument("url")
def web_extract(model, template, url, output, output_format, show_prompt,
                max_gen_len, temperature, top_p, **kwargs):
    """Extract knowledge from web page."""
    logging.info(f"Creating for {template}")

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    web_client = SoupClient()
    text = web_client.text(url)

    logging.debug(f"Input text: {text}")
    results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                   max_gen_len=max_gen_len,
                                   temperature=temperature,
                                   top_p=top_p)
    write_extraction(results, output, output_format)


@main.command()
@output_option_wb
@click.option("--dictionary")
@output_format_options
@click.option(
    "--recipes-urls-file",
    "-R",
    help="File with URLs to recipes to use for extraction",
)
@click.option("--auto-prefix", default="AUTO", help="Prefix to use for auto-generated classes.")
@model_option
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.argument("url")
def recipe_extract(
    model, url, recipes_urls_file, dictionary, output, output_format,
    show_prompt, max_gen_len, temperature, top_p, **kwargs
):
    """Extract from recipe on the web."""
    try:
        from recipe_scrapers import scrape_me
    except ModuleNotFoundError as e:
        logging.error(
            f"Did not find recipe_scrapers. Try: poetry install extras=recipes. Error: {e}"
        )

    template = "recipe"

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)
        if settings.cache_db:
            ke.client.cache_db_path = settings.cache_db
        if settings.skip_annotators:
            ke.skip_annotators = settings.skip_annotators

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    if recipes_urls_file:
        with open(recipes_urls_file, "r") as f:
            urls = [line.strip() for line in f.readlines() if url in line]
            if len(urls) != 1:
                raise ValueError(f"Found {len(urls)} URLs in {recipes_urls_file}")
            url = urls[0]
    scraper = scrape_me(url)

    logging.info(f"Creating for {template}")

    if dictionary:
        ke.load_dictionary(dictionary)
    ingredients = "\n".join(scraper.ingredients())
    instructions = "\n".join(scraper.instructions_list())
    text = f"""
    Recipe: {scraper.title()}
    Ingredients:\n{ingredients}
    Instructions:\n{instructions}
    """
    logging.info(f"Input text: {text}")
    results = ke.extract_from_text(text=text, show_prompt=show_prompt,
                                   max_gen_len=max_gen_len,
                                   temperature=temperature,
                                   top_p=top_p)
    logging.debug(f"Results: {results}")
    results.extracted_object.url = url
    write_extraction(results, output, output_format, ke)


@main.command()
@model_option
@output_option_wb
@output_format_options
@click.argument("input")
def convert(model, input, output, output_format, **kwargs):
    """Convert output format.

    Primarily intended for use with recipe template.
    """
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template, **kwargs)

    elif model_source == "GPT4All":
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    template = "recipe"
    logging.info(f"Creating for {template}")

    class_def = ke.template_pyclass
    with open(input, "r") as f:
        data = yaml.safe_load(f)
    obj = class_def(**data["extracted_object"])
    results = ExtractionResult(extracted_object=obj)
    write_extraction(results, output, output_format, ke)


@main.command()
@model_option
@output_option_txt
@output_format_options
@click.option(
    "-C", "--context", required=True, help="domain e.g. anatomy, industry, health-related"
)
@click.argument("term")
def synonyms(model, term, context, output, output_format, **kwargs):
    """Extract synonyms."""
    logging.info(f"Creating for {term}")

    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO Make SynonymEngine work without OpenAI, and change the
        # model_source here
        if model_source != "OpenAI":
            raise NotImplementedError("Model not yet supported for this function.")

    ke = SynonymEngine()
    out = str(ke.synonyms(term, context))
    output.write(out)


@main.command()
@output_option_txt
@output_format_options
@click.option(
    "--annotation-path",
    "-A",
    required=True,
)
@click.argument("term")
def create_gene_set(term, output, output_format, annotation_path, **kwargs):
    """Create a gene set."""
    logging.info(f"Creating for {term}")
    evaluator = EvalEnrichment()
    evaluator.load_annotations(annotation_path)
    gene_set = evaluator.create_gene_set_from_term(term)
    print(yaml.dump(gene_set.dict(), sort_keys=False))


@main.command()
@output_option_txt
@output_format_options
@click.option("--fill/--no-fill", default=False)
@click.option(
    "--input-file",
    "-U",
    help="File with gene IDs to enrich (if not passed as arguments)",
)
def convert_geneset(input_file, output, output_format, fill, **kwargs):
    """Convert gene set to YAML."""
    gene_set = parse_gene_set(input_file)
    if fill:
        fill_missing_gene_set_values(gene_set)
    output.write(dump_minimal_yaml(gene_set.dict()))


@main.command()
@output_option_txt
@output_format_options
@model_option
@show_prompt_option
@click.option(
    "--resolver", "-r", help="OAK selector for the gene ID resolver. E.g. sqlite:obo:hgnc"
)
@click.option(
    "-C",
    "--context",
    help="domain e.g. anatomy, industry, health-related (NOT IMPLEMENTED - currently gene only)",
)
@click.option(
    "--strict/--no-strict",
    default=True,
    show_default=True,
    help="If set, there must be a unique mappings from labels to IDs",
)
@click.option(
    "--input-file",
    "-U",
    help="File with gene IDs to enrich (if not passed as arguments)",
)
@click.option(
    "--randomize-gene-descriptions-using-file",
    help="FOR EVALUATION ONLY. Swap out gene descriptions with genes from this gene set filefile",
)
@click.option(
    "--ontological-synopsis/--no-ontological-synopsis",
    default=True,
    show_default=True,
    help="If set, use automated rather than manual gene descriptions",
)
@click.option(
    "--combined-synopsis/--no-combined-synopsis",
    default=False,
    show_default=True,
    help="If set, both gene descriptions",
)
@click.option(
    "--end-marker",
    help="For testing minor variants of prompts",
)
@click.option(
    "--annotations/--no-annotations",
    default=True,
    show_default=True,
    help="If set, include annotations in the prompt",
)
@prompt_template_option
@interactive_option
@click.argument("genes", nargs=-1)
def enrichment(
    genes,
    context,
    input_file,
    resolver,
    output,
    model,
    show_prompt,
    interactive,
    end_marker,
    output_format,
    randomize_gene_descriptions_using_file,
    **kwargs,
):
    """Gene class summary enriching (SPINDOCTOR).

    Algorithm:

    1. Map gene symbols to IDs using the resolver (unless IDs specified)
    2. Fetch gene descriptions using Alliance API
    3. Create a prompt using descriptions

    Limitations:

    It is very easy to exceed the max token length with GPT-3 models.

    Usage:

        ontollm enrichment -r sqlite:obo:hgnc -U tests/input/genesets/dopamine.yaml

    Usage:

        ontollm enrichment -r sqlite:obo:hgnc -U tests/input/genesets/dopamine.yaml
    """
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO Make EnrichmentEngine work without OpenAI, and change the
        # model_source here
        if model_source != "OpenAI":
            raise NotImplementedError(
                "Model not yet supported for gene enrichment or enrichment evaluation."
            )

    if not genes and not input_file:
        raise ValueError("Either genes or input file must be passed")
    if genes:
        gene_set = GeneSet(name="TEMP", gene_symbols=genes)
    if input_file:
        if genes:
            raise ValueError("Either genes or input file must be passed")
        gene_set = parse_gene_set(input_file)
    if not gene_set:
        raise ValueError("No genes passed")
    ke = create_engine(None, EnrichmentEngine, model=model)
    if end_marker:
        ke.end_marker = end_marker
    if interactive:
        ke.client.interactive = True
    if settings.cache_db:
        ke.client.cache_db_path = settings.cache_db
    if not isinstance(ke, EnrichmentEngine):
        raise ValueError(f"Expected EnrichmentEngine, got {type(ke)}")
    if resolver:
        ke.add_resolver(resolver)
    if randomize_gene_descriptions_using_file:
        print("WARNING!! Randomly spiking gene descriptions")
        spike_gene_set = parse_gene_set(randomize_gene_descriptions_using_file)
        aliases = {}
        if not spike_gene_set.gene_symbols:
            raise ValueError("No gene symbols for spike set")
        syms = copy(gene_set.gene_symbols)
        if len(spike_gene_set.gene_symbols) < len(gene_set.gene_symbols):
            raise ValueError("Not enough genes in spike set")
        for sym in spike_gene_set.gene_symbols:
            if not syms:
                break
            aliases[sym] = syms.pop()
        results = ke.summarize(
            spike_gene_set, normalize=resolver is not None, gene_aliases=aliases, **kwargs
        )
    else:
        results = ke.summarize(gene_set, normalize=resolver is not None, **kwargs)
    if results.truncation_factor is not None and results.truncation_factor < 1.0:
        logging.warning(f"Text was truncated; factor = {results.truncation_factor}")
    output = _as_text_writer(output)
    if show_prompt:
        print(results.prompt)
    output.write(dump_minimal_yaml(results))


@main.command()
@output_option_txt
@output_format_options
@model_option
@click.option(
    "-C",
    "--context",
    help="domain e.g. anatomy, industry, health-related (NOT IMPLEMENTED - currently gene only)",
)
@click.argument("text", nargs=-1)
def embed(text, context, output, model, output_format, **kwargs):
    """Embed text.

    Not currently supported for open models.
    """
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO: Check if this message is no longer necessary?
        if model_source != "OpenAI":
            raise NotImplementedError("Model not yet supported for embeddings.")
    else:
        model = "text-embedding-ada-002"

    if not text:
        raise ValueError("Text must be passed")
    client = HFHubClient(model=model)
    resp = client.embeddings(text)
    print(resp)


@main.command()
@output_option_txt
@output_format_options
@model_option
@click.option(
    "-C",
    "--context",
    help="domain e.g. anatomy, industry, health-related (NOT IMPLEMENTED - currently gene only)",
)
@click.argument("text", nargs=-1)
def text_similarity(text, context, output, model, output_format, **kwargs):
    """Embed text.

    Not currently supported for open models.
    """
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO: Check if this message is no longer necessary?
        if model_source != "OpenAI":
            raise NotImplementedError("Model not yet supported for embeddings.")
    else:
        model = "text-embedding-ada-002"

    if not text:
        raise ValueError("Text must be passed")
    text = list(text)
    if "@" not in text:
        raise ValueError("Text must contain @")
    ix = text.index("@")
    text1 = " ".join(text[:ix])
    text2 = " ".join(text[ix + 1 :])
    print(text1)
    print(text2)
    client = HFHubClient(model=model)
    sim = client.similarity(text1, text2, model=model)
    print(sim)


@main.command()
@output_option_txt
@output_format_options
@model_option
@click.option(
    "-C",
    "--context",
    help="domain e.g. anatomy, industry, health-related (NOT IMPLEMENTED - currently gene only)",
)
@click.argument("text", nargs=-1)
def text_distance(text, context, output, model, output_format, **kwargs):
    """Embed text and calculate euclidean distance between embeddings.

    Not currently supported for open models.
    """
    # TODO: Check that we do support this already?
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO: Check if this message is no longer necessary?
        if model_source != "OpenAI":
            raise NotImplementedError("Model not yet supported for embeddings.")
    else:
        model = "text-embedding-ada-002"

    if not text:
        raise ValueError("Text must be passed")
    text = list(text)
    if "@" not in text:
        raise ValueError("Text must contain @")
    ix = text.index("@")
    text1 = " ".join(text[:ix])
    text2 = " ".join(text[ix + 1 :])
    print(text1)
    print(text2)
    client = HFHubClient(model=model)
    sim = client.euclidean_distance(text1, text2, model=model)
    print(sim)


@main.command()
@output_option_txt
@output_format_options
@model_option
@click.option("--ontology", "-r", help="Ontology to use")
@click.option(
    "--definitions/--no-definitions",
    default=True,
    show_default=True,
    help="Include text definitions in the text to embed",
)
@click.option(
    "--parents/--no-parents",
    default=True,
    show_default=True,
    help="Include is-a parent terms in the text to embed",
)
@click.option(
    "--ancestors/--no-ancestors",
    default=True,
    show_default=True,
    help="Include all ancestors in the text to embed",
)
@click.option(
    "--logical-definitions/--no-logical-definitions",
    default=True,
    show_default=True,
    help="Include logical definitions in the text to embed",
)
@click.option(
    "--autolabel/--no-autolabel",
    default=True,
    show_default=True,
    help="Add subj/obj labels to report objects",
)
@click.option(
    "--synonyms/--no-synonyms",
    default=True,
    show_default=True,
    help="Include synonyms in the text to embed",
)
@click.argument("terms", nargs=-1)
def entity_similarity(terms, ontology, output, model, output_format, **kwargs):
    """Embed text.

    Not currently supported for open models.
    """
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO: Check if this message is no longer necessary?
        if model_source != "OpenAI":
            raise NotImplementedError("Model not yet supported for embeddings.")

    if not terms:
        raise ValueError("terms must be passed")
    terms = list(terms)
    if "@" not in terms:
        logging.info("No @ found, assuming all by all")
        terms1 = list(terms)
        terms2 = list(terms)
    else:
        ix = terms.index("@")
        terms1 = terms[:ix]
        terms2 = terms[ix + 1 :]
    adapter = get_adapter(ontology)
    entities1 = list(query_terms_iterator(terms1, adapter))
    entities2 = list(query_terms_iterator(terms2, adapter))

    engine = SimilarityEngine(model=model, adapter=adapter, **kwargs)
    writer = StreamingCsvWriter(output, heterogeneous_keys=False)

    for e1 in entities1:
        sims = engine.search(e1, entities2)
        for sim in sims:
            writer.emit(sim)


@main.command()
@inputfile_option
@output_option_txt
@model_option
@max_gen_len_option
@click.option("--task-file")
@click.option("--task-type")
@click.option("--tsv-output")
@click.option("--all-methods/--no-all-methods", default=False)
@click.option("--explain/--no-explain", default=False)
@click.option("--evaluate/--no-evaluate", default=False)
@click.argument("terms", nargs=-1)
def reason(
    terms,
    inputfile,
    model,
    task_file,
    explain,
    task_type,
    output,
    tsv_output,
    all_methods,
    evaluate,
    max_gen_len,
    **kwargs,
):
    """Reason."""
    reasoner = ReasonerEngine(model=model)
    if task_file:
        tc = extractor.TaskCollection.load(task_file)
    else:
        adapter = get_adapter(inputfile)
        if not isinstance(adapter, OboGraphInterface):
            raise ValueError("Only OBO graphs supported")
        ex = extractor.OntologyExtractor(adapter=adapter)
        # ex.use_identifiers = True
        task = ex.create_task(task_type=task_type, parameters=list(terms))
        tc = extractor.TaskCollection(tasks=[task])
    if all_methods:
        tasks = []
        print(f"Cloning {len(tc.tasks)} tasks")
        for core_task in tc.tasks:
            for m in extractor.GPTReasonMethodType:
                print(f"Cloning {m}")
                task = deepcopy(core_task)
                task.method = m
                task.init_method()
                tasks.append(task)
        tc.tasks = tasks
        print(f"New {len(tc.tasks)} tasks")
    else:
        for task in tc.tasks:
            task.include_explanations = explain
    resultset = reasoner.reason_multiple(tc, max_gen_len=max_gen_len,
                                         evaluate=evaluate)
    dump_minimal_yaml(resultset.dict(), file=output)
    if tsv_output:
        write_obj_as_csv(resultset.results, tsv_output)


@main.command()
@output_option_txt
@model_option
@click.argument("phenopacket_files", nargs=-1)
def diagnose(
    phenopacket_files,
    model,
    output,
    **kwargs,
):
    """Diagnose a clinical case represented as one or more Phenopackets."""
    phenopackets = [json.load(open(f)) for f in phenopacket_files]
    engine = PhenoEngine(model=model)
    results = engine.evaluate(phenopackets)
    print(dump_minimal_yaml(results))
    write_obj_as_csv(results, output)


@main.command()
@inputfile_option
@output_option_txt
@model_option
@click.option("--tsv-output")
@click.option("--template-path")
def answer(
    inputfile,
    model,
    template_path,
    output,
    tsv_output,
    **kwargs,
):
    """Answer a set of questions defined in YAML."""
    qc = QuestionCollection(**yaml.safe_load(open(inputfile)))
    engine = GenericEngine(model=model)
    qs = []
    for q in engine.run(qc, template_path=template_path):
        print(dump_minimal_yaml(q))
        qs.append(q)
    qc.questions = qs
    output.write(dump_minimal_yaml(qs))
    if tsv_output:
        write_obj_as_csv(qs, tsv_output)


@main.command()
@inputfile_option
@output_option_txt
@model_option
@click.option("--task-file")
@click.option("--task-type")
@click.option("--tsv-output")
@click.option("--yaml-output")
@click.option("--all-methods/--no-all-methods", default=False)
@click.option("--explain/--no-explain", default=False)
@click.option("--evaluate/--no-evaluate", default=False)
def categorize_mappings(
    inputfile,
    model,
    task_file,
    explain,
    task_type,
    output,
    tsv_output,
    yaml_output,
    all_methods,
    evaluate,
    **kwargs,
):
    """Categorize a collection of SSSOM mappings."""
    mapper = MappingEngine(model=model)
    if tsv_output:
        tc = mapper.from_sssom(inputfile)
        for cm in mapper.run_tasks(tc, evaluate=evaluate):
            print(dump_minimal_yaml(cm.dict()))
            # dump_minimal_yaml(cm.dict(), file=output)
        # write_obj_as_csv(resultset.results, tsv_output)
    else:
        import sssom.writers as sssom_writers

        msdf = parse_sssom_table(inputfile)
        msd = to_mapping_set_document(msdf)
        mappings = []
        cms = []
        done = []
        for mapping in msd.mapping_set.mappings:
            pair = mapping.subject_id, mapping.object_id
            if pair in done:
                continue
            mapping, cm = mapper.categorize_sssom_mapping(mapping)
            mappings.append(mapping)
            cms.append(cm.dict())
            done.append(pair)
        msd.mapping_set.mappings = mappings
        msdf = to_mapping_set_dataframe(msd)
        sssom_writers.write_table(msdf, output)
        if yaml_output:
            with open(yaml_output, "w") as file:
                dump_minimal_yaml(cms, file=file)


@main.command()
@output_option_txt
@click.option(
    "--strict/--no-strict",
    default=True,
    show_default=True,
    help="If set, there must be a unique mappings from labels to IDs",
)
@click.option(
    "--input-file",
    "-U",
    help="File with gene IDs to enrich (if not passed as arguments)",
)
@click.option(
    "--ontological-synopsis/--no-ontological-synopsis",
    default=True,
    show_default=True,
    help="If set, use automated rather than manual gene descriptions",
)
@click.option(
    "--combined-synopsis/--no-combined-synopsis",
    default=False,
    show_default=True,
    help="If set, both gene descriptions",
)
@click.option(
    "--annotations/--no-annotations",
    default=True,
    show_default=True,
    help="If set, include annotations in the prompt",
)
@click.option(
    "--number-to-drop",
    "-n",
    type=click.types.INT,
    default=1,
    help="Max number of genes to drop",
)
# @click.option(
#    "--randomize-gene-descriptions/--no-randomize-gene-descriptions",
#    help="DO NOT USE EXCEPT FOR EVALUATION PUPOSES."
# )
@click.option(
    "--annotations-path",
    "-A",
    help="Path to annotations",
)
@model_option
@click.argument("genes", nargs=-1)
def eval_enrichment(genes, input_file, number_to_drop, annotations_path, model, output, **kwargs):
    """Run enrichment using multiple methods."""
    if model:
        selectmodel = get_model_by_name(model)
        model_source = selectmodel["provider"]

        # TODO Make EnrichmentEngine work without OpenAI, and change the
        # model_source here
        if model_source != "OpenAI":
            raise NotImplementedError(
                "Model not yet supported for gene enrichment or enrichment evaluation."
            )

    if not genes and not input_file:
        raise ValueError("Either genes or input file must be passed")
    if genes:
        gene_set = GeneSet(name="TEMP", gene_symbols=genes)
    if input_file:
        if genes:
            raise ValueError("Either genes or input file must be passed")
        gene_set = parse_gene_set(input_file)
    if not gene_set:
        raise ValueError("No genes passed")
    fill_missing_gene_set_values(gene_set)
    if not annotations_path:
        if not _is_human(gene_set):
            raise ValueError("No annotations path passed")
        annotations_path = "tests/input/genes2go.tsv.gz"
    eval_engine = EvalEnrichment(model=model)
    eval_engine.load_annotations(annotations_path)
    comps = eval_engine.evaluate_methods_on_gene_set(gene_set, n=number_to_drop, **kwargs)
    output.write(dump_minimal_yaml(comps))


@main.command()
@recurse_option
@output_option_txt
@output_format_options
@click.option(
    "--num-tests",
    type=click.INT,
    default=5,
    show_default=True,
    help="number of iterations to cycle through.",
)
@click.argument("evaluator")
def eval(evaluator, num_tests, output, output_format, **kwargs):
    """Evaluate an extractor."""
    logging.info(f"Creating for {evaluator}")
    evaluator = create_evaluator(evaluator)
    evaluator.num_tests = num_tests
    eos = evaluator.eval()
    output.write(dump_minimal_yaml(eos, minimize=False))


@main.command()
@template_option
@model_option
@click.option("-E", "--examples", type=click.File("r"), help="File of example objects.")
@recurse_option
@output_option_wb
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.argument("object")
def fill(model, template, object: str, examples, output, output_format,
         show_prompt, max_gen_len, temperature, top_p, **kwargs):
    """Fill in missing values."""
    logging.info(f"Creating for {template}")

    ke: KnowledgeEngine

    # Choose model based on input, or use the default
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]

    # TODO Make SPIRESEngine work without OpenAI, and change the model_source
    # here
    if model_source == "OpenAI":
        ke = SPIRESEngine(template=template, **kwargs)
    else:
        model_name = selectmodel["alternative_names"][0]
        ke = GPT4AllEngine(template=template, model=model_name, **kwargs)

    an_object = yaml.safe_load(object)
    logging.info(f"Object to fill =  {object}")
    logging.info(f"Loading {examples}")
    examples = yaml.safe_load(examples)
    logging.debug(f"Input object: {object}")
    results = ke.generalize(an_object=an_object, examples=examples,
                            show_prompt=show_prompt,
                            max_gen_len=max_gen_len,
                            temperature=temperature,
                            top_p=top_p)

    output.write(yaml.dump(results.dict()))


@main.command()
@model_option
@output_option_txt
@output_format_options
@show_prompt_option
@max_gen_len_option
@temperature_option
@top_p_option
@click.argument("input")
def complete(model, input, output, output_format, show_prompt,
             max_gen_len, temperature, top_p, **kwargs):
    """Prompt completion."""
    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]
    model_name = selectmodel["alternative_names"][0]

    text = open(input).read()

    # TODO: Check that we can get rid of OpenAI here
    if model_source == "OpenAI":
        c = OpenAIClient(model=model_name)
        results = c.complete(prompt=text, show_prompt=show_prompt,
                max_gen_len=max_gen_len, temperature=temperature, top_p=top_p)

    elif model_source == "GPT4All":
        c = set_up_gpt4all_model(modelname=model_name)
        results = chain_gpt4all_model(model=c, prompt_text=text)

    output.write(results)


@main.command()
@template_option
@click.option("--input", "-i", type=click.File("r"), default=sys.stdin, help="Input file")
def parse(template, input):
    """Parse LLM results."""
    logging.info(f"Creating for {template}")
    ke = SPIRESEngine(template)
    text = input.read()
    logging.debug(f"Input text: {text}")
    # ke.annotator = BioPortalImplementation()
    results = ke.parse_completion_payload(text)
    print(yaml.dump(results))


@main.command()
@click.option("-o", "--output", type=click.File(mode="w"), default=sys.stdout, help="Output file.")
@output_format_options
@model_option
@click.option("-m", "match", help="Match string to use for filtering.")
@click.option("-D", "database", help="Path to sqlite database.")
def dump_completions(model, match, database, output, output_format):
    """Dump cached completions."""
    if model:
        raise NotImplementedError("Caching not currently enabled for this model.")
    else:
        # TODO Use some other client
        client = OpenAIClient()

    if database:
        client.cache_db_path = database
    if output_format == "jsonl":
        writer = jsonlines.Writer(output)
        for _engine, prompt, completion in client.cached_completions(match):
            writer.write(dict(engine=model, prompt=prompt, completion=completion))
    elif output_format == "yaml":
        for _engine, prompt, completion in client.cached_completions(match):
            output.write(
                dump_minimal_yaml(dict(engine=model, prompt=prompt, completion=completion))
            )
    else:
        output.write("# Cached Completions:\n")
        for engine, prompt, completion in client.cached_completions(match):
            output.write("## Entry\n")
            output.write(f"### Engine: {engine}\n")
            output.write(f"### Prompt:\n\n {prompt}\n\n")
            output.write(f"### Completion:\n\n {completion}\n\n")


@main.command()
@click.option("-o", "--output", type=click.File(mode="w"), default=sys.stdout, help="Output file.")
@click.argument("input", type=click.File("r"))
def convert_examples(input, output):
    """Convert training examples from YAML."""
    logging.info(f"Creating examples for {input}")
    example_doc = yaml.safe_load(input)
    writer = jsonlines.Writer(output)
    for example in example_doc["examples"]:
        prompt = example["prompt"]
        completion = yaml.dump(example["completion"], sort_keys=False)
        writer.write(dict(prompt=prompt, completion=completion))


@main.command()
@model_option
@click.option("-o", "--output", type=click.File(mode="w"), default=sys.stdout, help="Output file.")
@click.option("-i", "--input", help="Input ontology.")
@click.option("-c", "--context", help="Context.")
@click.option(
    "--num-iterations",
    type=click.INT,
    default=5,
    show_default=True,
    help="number of iterations to cycle through.",
)
@click.argument("terms", nargs=-1)
def halo(model, input, context, terms, output, **kwargs):
    """Run HALO over inputs."""
    if model:
        raise NotImplementedError("HALO not currently supported for this model.")

    engine = HALOEngine()
    engine.seed_from_file(input)
    if context is None:
        context = engine.ontology.elements[0].context
    engine.fixed_slot_values = {"context": context}
    engine.hallucinate(terms, **kwargs)
    output.write(dump_minimal_yaml(engine.ontology))


@main.command()
@model_option
@output_option_wb
@output_format_options
@show_prompt_option
@click.option(
    "-d",
    "--description",
    help="domain e.g. anatomy, industry, health-related (NOT IMPLEMENTED - currently gene only)",
)
@click.option(
    "--sections", multiple=True, help="sections to include e.g. medications, vital signs, etc."
)
def clinical_notes(
    description,
    sections,
    output,
    model,
    show_prompt,
    output_format,
    **kwargs,
):
    """Create mock clinical notes.

    Example:

        ontollm clinical-notes -d "middle-aged female patient with diabetes"
        ontollm clinical-notes --description "middle-aged female patient with diabetes"\
         --sections medications --sections "vital signs"

    """
    prompt = "create mock clinical notes for a patient like this: " + description
    if sections:
        prompt += " including sections: " + ", ".join(sections)

    if not model:
        model = DEFAULT_MODEL
    selectmodel = get_model_by_name(model)
    model_source = selectmodel["provider"]
    model_name = selectmodel["alternative_names"][0]

    if model_source == "GPT4All":
        c = set_up_gpt4all_model(modelname=model_name)
        results = chain_gpt4all_model(model=c, prompt_text=prompt)

    output.write(results)


@main.command()
def list_templates():
    """List the templates."""
    print("TODO")


@main.command()
def list_models():
    """List all available models."""
    print("Model Name\tProvider\tAlternative Names\tStatus\tDisk Space\tSystem Memory")
    for model in MODELS:
        primary_name = model["name"]
        provider = model["provider"]
        alternative_names = (
            " ".join(model["alternative_names"]) if model["alternative_names"] else ""
        )
        if "not_implemented" in model or "deprecated" in model:
            status = "Not Implemented"
        else:
            status = "Implemented"
        disk = model["requirements"]["diskspace"]
        memory = model["requirements"]["memory"]

        print(f"{primary_name}\t{provider}\t{alternative_names}\t{status}\t{disk}\t{memory}")


if __name__ == "__main__":
    main()
