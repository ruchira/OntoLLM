"""
Main Knowledge Extractor class.

This works by recursively constructing structured prompt-completions where
a pseudo-YAML structure is requested, where the YAML
structure corresponds to a template class.

Describe in the SPIRES manuscript
TODO: add link
"""
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import pydantic
import yaml
from linkml_runtime.linkml_model import ClassDefinition, SlotDefinition
from oaklib import BasicOntologyInterface

from ontollm.engines.knowledge_engine import (
    ANNOTATION_KEY_PROMPT,
    ANNOTATION_KEY_PROMPT_SKIP,
    EXAMPLE,
    FIELD,
    OBJECT,
    KnowledgeEngine,
    chunk_text,
)
from ontollm.io.yaml_wrapper import dump_minimal_yaml
from ontollm.templates.core import ExtractionResult

this_path = Path(__file__).parent


RESPONSE_ATOM = Union[str, "ResponseAtom"]  # type: ignore
RESPONSE_DICT = Dict[FIELD, Union[RESPONSE_ATOM, List[RESPONSE_ATOM]]]


@dataclass
class SPIRESEngine(KnowledgeEngine):
    """Knowledge extractor."""

    recurse: bool = True
    """If true, then complex non-named entity objects are always recursively parsed.
    If this is false AND the complex object is a pair, then token-based splitting is
    instead used.
    TODO: deprecate this, it's not clear that token-based splitting is better, due to
    the inability to control which tokens the LLM will use"""

    sentences_per_window: Optional[int] = None
    """If set, this will split the text into chains of sentences,
    where this value determines the maximum number of sentences per chain.
    The results are then merged together."""

    def extract_from_text(
        self,
        text: str,
        show_prompt: bool = False,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
        class_def: ClassDefinition = None,
        an_object: OBJECT = None,
    ) -> ExtractionResult:
        """
        Extract annotations from the given text.

        :param text:
        :param class_def:
        :param an_object: optional stub object
        :return:
        """
        if self.sentences_per_window:
            chunks = chunk_text(text, self.sentences_per_window)
            extracted_object = None
            for chunk in chunks:
                raw_text = self._raw_extract(chunk, class_def=class_def,
                                             an_object=an_object,
                                             show_prompt=show_prompt,
                                             max_gen_len=max_gen_len,
                                             temperature=temperature,
                                             top_p=top_p,)
                logging.info(f"RAW TEXT: {raw_text}")
                next_object = self.parse_completion_payload(
                    raw_text, class_def, an_object=an_object  # type: ignore
                )
                if extracted_object is None:
                    extracted_object = next_object
                else:
                    for k, v in next_object.items():
                        if isinstance(v, list):
                            extracted_object[k] += v
                        else:
                            if k not in extracted_object:
                                extracted_object[k] = v
                            else:
                                extracted_object[k] = v
        else:
            raw_text = self._raw_extract(text=text, class_def=class_def,
                                         show_prompt=show_prompt,
                                         max_gen_len=max_gen_len,
                                         temperature=temperature,
                                         top_p=top_p,
                                         an_object=an_object)
            logging.info(f"RAW TEXT: {raw_text}")
            extracted_object = self.parse_completion_payload(
                raw_text, class_def, an_object=an_object  # type: ignore
            )
        return ExtractionResult(
            input_text=text,
            raw_completion_output=raw_text,
            prompt=self.last_prompt,
            extracted_object=extracted_object,
            named_entities=self.named_entities,
        )

    def _extract_from_text_to_dict(self, text: str,
                                   class_def: ClassDefinition = None,
                                   max_gen_len: int = 4097,
                                   temperature: float = 0.6,
                                   top_p: float = 0.9,
                                   ) -> RESPONSE_DICT:
        raw_text = self._raw_extract(text,
                                     class_def=class_def,
                                     max_gen_len=max_gen_len,
                                     temperature=temperature,
                                     top_p=top_p, 
                                     )
        return self._parse_response_to_dict(raw_text, class_def)

    def generate_and_extract(
        self, entity: str, show_prompt: bool = False, prompt_template: str = None,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
        **kwargs
    ) -> ExtractionResult:
        """
        Generate a description using the LLM, then extract from it using SPIRES.

        :param entity:
        :param kwargs:
        :return:
        """
        if prompt_template is None:
            prompt_template = "Generate a comprehensive description of {entity}.\n"
        prompt = prompt_template.format(entity=entity)
        if self.client is not None:
            payload = self.client.complete(prompt, show_prompt,
                                       max_gen_len=max_gen_len,
                                       temperature=temperature,
                                       top_p=top_p)
        else:
            payload = ""
        return self.extract_from_text(payload, **kwargs)

    def iteratively_generate_and_extract(
        self,
        entity: str,
        cache_path: Union[str, Path],
        iteration_slots: List[str],
        adapter: BasicOntologyInterface = None,
        clear=False,
        max_iterations=10,
        prompt_template=None,
        show_prompt: bool = False,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
        **kwargs,
    ) -> Iterator[ExtractionResult]:
        def _remove_parenthetical_context(s: str):
            return re.sub(r"\(.*\)", "", s)

        iteration = 0
        if isinstance(cache_path, str):
            cache_path = Path(cache_path)
        if cache_path.exists() and not clear:
            db = yaml.safe_load(cache_path.open())
            if "entities_in_queue" not in db:
                db["entities_in_queue"] = []
        else:
            db = {"processed_entities": [], "entities_in_queue": [], "results": []}
        if entity not in db["processed_entities"]:
            db["entities_in_queue"].append(entity)
        if prompt_template is None:
            prompt_template = (
                "Generate a comprehensive description of {entity}. "
                + "The description should include the information on"
                + " and ".join(iteration_slots)
                + ".\n"
            )
        while db["entities_in_queue"] and iteration < max_iterations:
            iteration += 1
            next_entity = db["entities_in_queue"].pop(0)
            logging.info(f"ITERATION {iteration}, entity={next_entity}")
            # check if entity matches a curie pattern using re
            if re.match(r"^[A-Z]+:[A-Z0-9]+$", next_entity):
                curie = next_entity
                next_entity = adapter.label(next_entity)
            else:
                curie = None
            result = self.generate_and_extract(
                next_entity, show_prompt=show_prompt,
                prompt_template=prompt_template,
                max_gen_len=max_gen_len,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            if curie:
                if result.extracted_object:
                    result.extracted_object.id = curie
            db["results"].append(result)
            db["processed_entities"].append(next_entity)
            yield result
            for s in iteration_slots:
                # if s not in result.extracted_object:
                #    raise ValueError(f"Slot {s} not found in {result.extracted_object}")
                vals = getattr(result.extracted_object, s, [])
                if not vals:
                    logging.info("dead-end: no values found for slot")
                    continue
                if not isinstance(vals, list):
                    vals = [vals]
                for val in vals:
                    entity = val
                    if result.named_entities is not None:
                        for ne in result.named_entities:
                            if ne.id == val:
                                entity = ne.label
                                if ne.id.startswith("AUTO"):
                                    # Sometimes the value of some slots will lack
                                    context = next_entity
                                    context = re.sub(r"\(.*\)", "", context)
                                    entity = f"{entity} ({context})"
                                else:
                                    entity = ne.id
                                break
                    queue_deparenthesized = [
                        _remove_parenthetical_context(e) for e in db["entities_in_queue"]
                    ]
                    if (
                        entity not in db["processed_entities"]
                        and entity not in db["entities_in_queue"]
                        and _remove_parenthetical_context(entity) not in queue_deparenthesized
                    ):
                        db["entities_in_queue"].append(entity)
            with open(cache_path, "w") as f:
                # TODO: consider a more robust backend e.g. mongo
                f.write(dump_minimal_yaml(db))

    def generalize(
        self,
        an_object: Union[pydantic.BaseModel, dict],
        examples: List[EXAMPLE],
        show_prompt: bool = False,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
    ) -> ExtractionResult:
        """
        Generalize the given examples.

        :param an_object:
        :param examples:
        :return:
        """
        class_def = self.template_class
        sv = self.schemaview
        prompt = "example:\n"
        for example in examples:
            prompt += f"{self.serialize_object(example)}\n\n"
        prompt += "\n\n===\n\n"
        if isinstance(an_object, pydantic.BaseModel):
            an_object = an_object.dict()
        for k, v in an_object.items():
            if v:
                slot = sv.induced_slot(k, class_def.name)
                prompt += f"{k}: {self._serialize_value(v, slot)}\n"
        logging.debug(f"PROMPT: {prompt}")
        payload = self.client.complete(prompt, show_prompt,
                                       max_gen_len, temperature, top_p)
        prediction = self.parse_completion_payload(payload, an_object=an_object)
        return ExtractionResult(
            input_text=prompt,
            raw_completion_output=payload,
            # prompt=self.last_prompt,
            results=[prediction],
            named_entities=self.named_entities,
        )

    def map_terms(
        self, terms: List[str], ontology: str, show_prompt: bool = False,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
    ) -> Dict[str, str]:
        """
        Map the given terms to the given ontology.

        EXPERIMENTAL

        currently some LLMs do not do so well with this task.

        :param terms:
        :param ontology:
        :return:
        """
        # TODO: make a separate config
        examples = {
            "go": {
                "nucleui": "nucleus",
                "mitochondrial": "mitochondrion",
                "signaling": "signaling pathway",
                "cysteine biosynthesis": "cysteine biosynthetic process",
                "alcohol dehydrogenase": "alcohol dehydrogenase activity",
            },
            "uberon": {
                "feet": "pes",
                "forelimb, left": "left forelimb",
                "hippocampus": "Ammons horn",
            },
        }
        ontology = ontology.lower()
        if ontology in examples:
            example = examples[ontology]
        else:
            example = examples["uberon"]
        prompt = "Normalize the following semicolon separated\
            list of terms to the {ontology.upper()} ontology\n\n"
        prompt += "For example:\n\n"
        for k, v in example.items():
            prompt += f"{k}: {v}\n"
        prompt += "===\n\nTerms:"
        prompt += "; ".join(terms)
        prompt += "===\n\n"
        payload = self.client.complete(prompt, show_prompt, max_gen_len,
                                       temperature, top_p)
        # outer parse
        best_results = []
        for sep in ["\n", "; "]:
            results = payload.split(sep)
            if len(results) > len(best_results):
                best_results = results

        def normalize(s: str) -> str:
            s = s.strip()
            s.replace("_", " ")
            return s.lower()

        mappings = {}
        for result in best_results:
            if ":" not in result:
                logging.error(f"Count not parse result: {result}")
                continue
            k, v = result.strip().split(":", 1)
            k = k.strip()
            v = v.strip()
            for t in terms:
                if normalize(t) == normalize(k):
                    mappings[t] = v
                    break
        for t in terms:
            if t not in mappings:
                logging.warning(f"Could not map term: {t}")
        return mappings

    def serialize_object(self, example: EXAMPLE, class_def: ClassDefinition = None) -> str:
        if class_def is None:
            class_def = self.template_class
        if isinstance(example, str):
            return example
        if isinstance(example, pydantic.BaseModel):
            example = example.dict()
        lines = []
        sv = self.schemaview
        for k, v in example.items():
            if not v:
                continue
            slot = sv.induced_slot(k, class_def.name)
            v_serialized = self._serialize_value(v, slot)
            lines.append(f"{k}: {v_serialized}")
        return "\n".join(lines)

    def _serialize_value(self, val: Any, slot: SlotDefinition) -> str:
        if val is None:
            return ""
        if isinstance(val, list):
            return "; ".join([self._serialize_value(v, slot) for v in val if v])
        if isinstance(val, dict):
            return " - ".join([self._serialize_value(v, slot) for v in val.values() if v])
        sv = self.schemaview
        if slot.range in sv.all_classes():
            if self.labelers:
                labelers = list(self.labelers)
            else:
                labelers = []
            labelers += self.get_annotators(sv.get_class(slot.range))
            if labelers:
                for labeler in labelers:
                    label = labeler.label(val)
                    if label:
                        return label
        return val

    def _raw_extract(
        self, 
        text, 
        class_def: ClassDefinition = None, 
        an_object: OBJECT = None
        show_prompt: bool = False,
        max_gen_len: int = 4097,
        temperature: float = 0.6,
        top_p: float = 0.9,
    ) -> str:
        """
        Extract annotations from the given text.

        :param text:
        :return:
        """
        prompt = self.get_completion_prompt(class_def, text, an_object=an_object)
        self.last_prompt = prompt
        payload = self.client.complete(prompt, show_prompt, max_gen_len,
                                       temperature, top_p)
        return payload

    def get_completion_prompt(
        self, class_def: ClassDefinition = None, text: str = None, an_object: OBJECT = None
    ) -> str:
        """Get the prompt for the given template."""
        if class_def is None:
            class_def = self.template_class
        if not text or ("\n" in text or len(text) > 60):
            prompt = (
                "From the text below, extract the following entities in the following format:\n\n"
            )
        else:
            prompt = "Split the following piece of text into fields in the following format:\n\n"
        for slot in self.schemaview.class_induced_slots(class_def.name):
            if ANNOTATION_KEY_PROMPT_SKIP in slot.annotations:
                continue
            if ANNOTATION_KEY_PROMPT in slot.annotations:
                slot_prompt = slot.annotations[ANNOTATION_KEY_PROMPT].value
            elif slot.description:
                slot_prompt = slot.description
            else:
                if slot.multivalued:
                    slot_prompt = f"semicolon-separated list of {slot.name}s"
                else:
                    slot_prompt = f"the value for {slot.name}"
            if slot.range in self.schemaview.all_enums():
                enum_def = self.schemaview.get_enum(slot.range)
                pvs = [str(k) for k in enum_def.permissible_values.keys()]
                slot_prompt += f"Must be one of: {', '.join(pvs)}"
            prompt += f"{slot.name}: <{slot_prompt}>\n"
        # prompt += "Do not answer if you don't know\n\n"
        prompt = f"{prompt}\n\nText:\n{text}\n\n===\n\n"
        if an_object:
            if class_def is None:
                class_def = self.template_class
            if isinstance(an_object, pydantic.BaseModel):
                an_object = an_object.dict()
            for k, v in an_object.items():
                if v:
                    slot = self.schemaview.induced_slot(k, class_def.name)
                    prompt += f"{k}: {self._serialize_value(v, slot)}\n"
        return prompt

    def _parse_response_to_dict(
        self, results: str, class_def: ClassDefinition = None
    ) -> Optional[RESPONSE_DICT]:
        """
        Parse the pseudo-YAML response from the LLM into a dictionary object.

        E.g.

            foo: a; b; c

        becomes

            {"foo": ["a", "b", "c"]}

        :param results:
        :return:
        """
        lines = results.splitlines()
        ann = {}
        promptable_slots = self.promptable_slots(class_def)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                if len(promptable_slots) == 1:
                    slot = promptable_slots[0]
                    logging.warning(
                        f"Coercing to YAML-like with key {slot.name}: Original line: {line}"
                    )
                    line = f"{slot.name}: {line}"
                else:
                    logging.error(f"Line '{line}' does not contain a colon; ignoring")
                    return None
            r = self._parse_line_to_dict(line, class_def)
            if r is not None:
                field, val = r
                ann[field] = val
        return ann

    def _parse_line_to_dict(
        self, line: str, class_def: ClassDefinition = None
    ) -> Optional[Tuple[FIELD, RESPONSE_ATOM]]:
        if class_def is None:
            class_def = self.template_class
        sv = self.schemaview
        # each line is a key-value pair
        logging.info(f"PARSING LINE: {line}")
        field, val = line.split(":", 1)
        # Field nornalization:
        # The LLML may mutate the output format somewhat,
        # randomly pluralizing or replacing spaces with underscores
        field = field.lower().replace(" ", "_")
        cls_slots = sv.class_slots(class_def.name)
        slot = None
        if field in cls_slots:
            slot = sv.induced_slot(field, class_def.name)
        else:
            # TODO: check this
            if field.endswith("s"):
                field = field[:-1]
            if field in cls_slots:
                slot = sv.induced_slot(field, class_def.name)
        if not slot:
            logging.error(f"Cannot find slot for {field} in {line}")
            # raise ValueError(f"Cannot find slot for {field} in {line}")
            return None
        if not val:
            msg = f"Empty value in key-value line: {line}"
            if slot.required:
                raise ValueError(msg)
            if slot.recommended:
                logging.warning(msg)
            return None
        inlined = slot.inlined
        slot_range = sv.get_class(slot.range)
        if not inlined:
            if slot.range in sv.all_classes():
                inlined = sv.get_identifier_slot(slot_range.name) is None
        val = val.strip()
        if slot.multivalued:
            vals = [v.strip() for v in val.split(";")]
        else:
            vals = [val]
        vals = [val for val in vals if val]
        logging.debug(f"SLOT: {slot.name} INL: {inlined} VALS: {vals}")
        if inlined:
            transformed = False
            slots_of_range = sv.class_slots(slot_range.name)
            if self.recurse or len(slots_of_range) > 2:
                logging.debug(f"  RECURSING ON SLOT: {slot.name}, range={slot_range.name}")
                vals = [
                    self._extract_from_text_to_dict(v, slot_range) for v in vals  # type: ignore
                ]
            else:
                for sep in [" - ", ":", "/", "*", "-"]:
                    if all([sep in v for v in vals]):
                        vals = [
                            dict(zip(slots_of_range, v.split(sep, 1))) for v in vals  # type: ignore
                        ]
                        for v in vals:
                            for k in v.keys():  # type: ignore
                                v[k] = v[k].strip()  # type: ignore
                        transformed = True
                        break
                if not transformed:
                    logging.warning(f"Did not find separator in {vals} for line {line}")
                    return None
        # transform back from list to single value if not multivalued
        if slot.multivalued:
            final_val = vals
        else:
            if len(vals) != 1:
                logging.error(f"Expected 1 value for {slot.name} in '{line}' but got {vals}")
            final_val = vals[0]  # type: ignore
        return field, final_val

    def parse_completion_payload(
        self, results: str, class_def: ClassDefinition = None, an_object: dict = None
    ) -> pydantic.BaseModel:
        """
        Parse the completion payload into a pydantic class.

        :param results:
        :param class_def:
        :param object: stub object
        :return:
        """
        raw = self._parse_response_to_dict(results, class_def)
        logging.debug(f"RAW: {raw}")
        if an_object:
            raw = {**an_object, **raw}
        self._auto_add_ids(raw, class_def)
        return self.ground_annotation_object(raw, class_def)

    def _auto_add_ids(self, ann: RESPONSE_DICT, class_def: ClassDefinition = None) -> None:
        if ann is None:
            return
        if class_def is None:
            class_def = self.template_class
        for slot in self.schemaview.class_induced_slots(class_def.name):
            if slot.identifier:
                if slot.name not in ann:
                    auto_id = str(uuid.uuid4())
                    auto_prefix = self.auto_prefix
                    if slot.range == "uriorcurie" or slot.range == "uri":
                        ann[slot.name] = f"{auto_prefix}:{auto_id}"
                    else:
                        ann[slot.name] = auto_id

    def ground_annotation_object(
        self, ann: RESPONSE_DICT, class_def: ClassDefinition = None
    ) -> Optional[pydantic.BaseModel]:
        """Ground the direct parse of the LLM payload.

        The raw LLM payload is a YAML-like string, which is parsed to
        a response dictionary.

        This dictionary is then grounded, using this method

        :param ann: Raw annotation object
        :param class_def: schema class the ground object should instantiate
        :return: Grounded annotation object
        """
        logging.debug(f"Grounding annotation object {ann}")
        if class_def is None:
            class_def = self.template_class
        sv = self.schemaview
        new_ann: Dict[str, Any] = {}
        if ann is None:
            logging.error(f"Cannot ground None annotation, class_def={class_def.name}")
            return None
        for field, vals in ann.items():
            if isinstance(vals, list):
                multivalued = True
            else:
                multivalued = False
                vals = [vals]
            slot = sv.induced_slot(field, class_def.name)
            rng_cls = sv.get_class(slot.range)
            enum_def = None
            if slot.range:
                if slot.range in self.schemaview.all_enums():
                    enum_def = self.schemaview.get_enum(slot.range)
            new_ann[field] = []
            logging.debug(f"FIELD: {field} SLOT: {slot.name}")
            for val in vals:
                if not val:
                    continue
                logging.debug(f"   VAL: {val}")
                if isinstance(val, tuple):
                    # special case for pairs
                    sub_slots = sv.class_induced_slots(rng_cls.name)
                    obj = {}
                    for i in range(0, len(val)):
                        sub_slot = sub_slots[i]
                        sub_rng = sv.get_class(sub_slot.range)
                        if not sub_rng:
                            logging.error(f"Cannot find range for {sub_slot.name}")
                        result = self.normalize_named_entity(val[i], sub_slot.range)
                        obj[sub_slot.name] = result
                elif isinstance(val, dict):
                    # recurse
                    obj = self.ground_annotation_object(val, rng_cls)
                else:
                    obj = self.normalize_named_entity(val, slot.range)  # type: ignore
                if enum_def:
                    found = False
                    logging.info(f"Looking for {obj} in {enum_def.name}")
                    for k, _pv in enum_def.permissible_values.items():
                        if type(obj) is str and type(k) is str:
                            if obj.lower() == k.lower():
                                obj = k  # type: ignore
                                found = True
                                break
                    if not found:
                        logging.info(f"Cannot find enum value for {obj} in {enum_def.name}")
                        obj = None
                if multivalued:
                    new_ann[field].append(obj)
                else:
                    new_ann[field] = obj
        logging.debug(f"Creating object from dict {new_ann}")
        logging.info(new_ann)
        py_cls = self.template_module.__dict__[class_def.name]
        return py_cls(**new_ann)
