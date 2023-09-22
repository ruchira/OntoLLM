"""Streamlist web app for spindoctor."""
# Import necessary libraries
import re

import streamlit as st
from oaklib import get_adapter

from ontogpt.engines import create_engine
from ontogpt.engines.enrichment import EnrichmentEngine, GeneDescriptionSource
from ontogpt.utils.gene_set_utils import GeneSet

MODEL_GPT_3_5_TURBO = "gpt-3.5-turbo"
MODEL_TEXT_DAVINCI_003 = "text-davinci-003"
MODEL_GPT_4 = "gpt-4"

go = get_adapter("sqlite:obo:go")

# Title of the app
st.title("SPINDOCTOR")
st.caption("A tool for summarizing gene sets using LLMs")

col1, col2 = st.columns(2)

# Text area for name input
gene_symbols = col1.text_area("Enter a list of human gene symbols")

model = col1.selectbox(
    "Select the model:", (MODEL_GPT_4_ALL_J_1_3_GROOVY, MODEL_FLAN_T5_XXL,
                          MODEL_FLAN_UL2, MODEL_FALCON_40B_INSTRUCT,
                          MODEL_BLOOM, MODEL_DOLLY_V2_12B)
)

source = col1.selectbox(
    "Select the gene description source:",
    (
        GeneDescriptionSource.ONTOLOGICAL_SYNOPSIS.value,
        GeneDescriptionSource.NARRATIVE_SYNOPSIS.value,
        GeneDescriptionSource.NONE.value,
    ),
)

# Button for parsing and displaying the names
if col1.button("Summarize genes"):
    gene_symbols = [symbol.strip() for symbol in re.split(r"[\-,;\s]+", gene_symbols)]
    gene_set = GeneSet(name="TEMP", gene_symbols=gene_symbols)
    ke = create_engine(None, EnrichmentEngine, model=model)
    if not isinstance(ke, EnrichmentEngine):
        raise ValueError(f"Expected EnrichmentEngine, got {type(ke)}")
    source_pv = GeneDescriptionSource(source)
    col1.write("Analyzing, please wait...")
    results = ke.summarize(gene_set, gene_description_source=source_pv)
    col1.header("Genes")
    for gene_id in gene_set.gene_ids:
        col1.write(f" * {gene_id}")
    # st.write("## Term Strings")
    # for term_string in results.term_strings:
    #    st.write(f" * {term_string}")
    col2.write("## Terms")
    for term_id in results.term_ids:
        if term_id.startswith("GO:"):
            lbl = go.label(term_id)
            col2.markdown(f" * [{term_id}](https://bioregistry.io/{term_id}) - _{lbl}_")
        else:
            col2.markdown(f" * UNPARSED {term_id}")
    col2.header("Summary")
    col2.caption(results.summary)
