"""Exporter."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TextIO, Union

from ontollm.templates.core import ExtractionResult

from linkml_runtime import SchemaView

def is_curie(s: str) -> bool:
    return ":" in s and " " not in s


@dataclass
class Exporter:
    def export(
        self,
        extraction_output: ExtractionResult,
        output: Union[str, Path, TextIO, BytesIO],
        schemaview: SchemaView,
    ):
        raise NotImplementedError
