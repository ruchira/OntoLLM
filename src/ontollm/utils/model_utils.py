"""Utilities for retrieving and applying prebuild models."""

import logging
from pathlib import PosixPath

import pystow

ONTOGPT_MODULE = pystow.module("ontollm")


def get_model(url: str) -> PosixPath:
    """Retrieve a model from a given URL.

    Returns the Path for the retrieved file,
    or the path to where it already exists.
    """
    logging.info(f"Retrieving model from {url} if needed...")
    mod_path = ONTOLLM_MODULE.ensure(url=url, force=False, download_kwargs={"backend": "requests"})
    logging.info(f"Model now at {mod_path}")

    return mod_path
