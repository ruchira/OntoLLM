"""Llama 2 Client."""

from dataclasses import dataclass
import glob
import logging
import os
from pathlib import Path
import sqlite3
from typing import Iterator, Tuple

from codellama.llama.generation import Llama
from codellama.llama.tokenizer import Tokenizer
from torch import Tensor, device

import numpy as np

LLAMA2_MAX_LEN = 16000

# This module is for interacting directly with a self-hosted Llama 2 model,
# together with a sentence embedding model.
# Alternatively, one can interact with Llama 2 via HuggingFace; see the
# HuggingFace Hub Client for that approach.

logger = logging.getLogger(__name__)


@dataclass
class Llama2Client:
    """A client for interacting with self-hosted Llama 2."""
    DOWNLOAD_FIRST_MSG: str = \
        """Please make sure you have cloned the llama repository, run
        download.sh, and downloaded some models, after having received
        the download email from Meta AI."""
    cache_db_path_str: str = None

    def __init__(self, checkpoint_dir_path: str, tokenizer_path: str,
                 max_seq_len : int = 512, max_batch_size : int = 8):
        self.checkpoint_dir_path = checkpoint_dir_path
        self.tokenizer_filepath = tokenizer_path
        self.max_seq_len = max_seq_len
        self.max_batch_size = max_batch_size
        if not os.path.exists(self.tokenizer_filepath):
            raise ValueError(
                f"Didn't find {self.tokenizer_filepath}.\n"
                + self.DOWNLOAD_FIRST_MSG)
        if not os.path.exists(self.checkpoint_dir_path):
            raise ValueError(
                f"Didn't find directory {self.checkpoint_dir_path}.\n"
                + self.DOWNLOAD_FIRST_MSG)
        self.llama = Llama.build(
            ckpt_dir=self.checkpoint_dir_path,
            tokenizer_path=self.tokenizer_filepath,
            max_seq_len=self.max_seq_len,
            max_batch_size=self.max_batch_size)
        self.model_name = os.path.basename(checkpoint_dir_path)

    def db_cursor(self):
        if not self.cache_db_path_str:
            self.cache_db_path_str = ".llama2_cache.db"
        cache_db_path = Path(self.cache_db_path_str)
        logger.info(f"Caching Llama 2 responses to {cache_db_path.absolute()}")
        should_create = not cache_db_path.exists()
        connection = sqlite3.connect(self.cache_db_path_str)
        cur = connection.cursor()
        if should_create:
            cur.execute("CREATE TABLE cache (user_prompt, system_prompt, payload)")
        return cur

    def complete(self, prompt : str,
                 show_prompt : bool = False,
                 max_gen_len: int = LLAMA2_MAX_LEN,
                 temperature: float = 0.6,
                 top_p: float = 0.9):
        """Complete text using a Llama 2 model."""
        logger.info(f"Complete: prompt[{len(prompt)}]={prompt[0:256]}...")
        if show_prompt:
            logger.info(f" SENDING PROMPT\n{prompt}")
        cur = self.db_cursor()
        cached = cur.execute("SELECT payload FROM cache WHERE user_prompt=:prompt",
                             {"prompt" : prompt})
        payload = cached.fetchone()
        if payload:
            prompt_peek = str(prompt)[0:80].replace("\n", "\\n")
            logger.info(f"Using cached payload for prompt: {prompt_peek}...")
            return payload[0]
        try:
            responses = self.llama.text_completion(
                [prompt],
                max_gen_len=max_gen_len,
                temperature=temperature,
                top_p=top_p,
            )
        except ValueError as e:
            logging.error(e)
            responses = []

        if len(responses) > 0:
            payload = responses[0]['generation']
            logger.info(f"Storing paylod of len: {len(payload)}")
            cur.execute("INSERT INTO cache (user_prompt, system_prompt, payload) VALUES (:user_prompt, NULL, :payload)",
                        {"user_prompt": prompt, "payload": payload})
            cur.connection.commit()
            return payload

        return ""

    def chat_completion(self, user_prompt: str, system_prompt: str = None,
                        show_prompt : bool = False,
                        max_gen_len: int = LLAMA2_MAX_LEN,
                        temperature: float = 0.2,
                        top_p: float = 0.9):
        """Chat to a Llama 2 model."""
        if system_prompt is not None:
            logger.info(f"Chat system: prompt[{len(prompt)}]={system_prompt[0:256]}...")
        logger.info(f"Chat user: prompt[{len(prompt)}]={user_prompt[0:256]}...")
        if show_prompt:
            logger.info(f" SENDING SYSTEM PROMPT\n{system_prompt}")
            logger.info(f" SENDING USER PROMPT\n{user_prompt}")
        cur = self.db_cursor()
        if system_prompt is None:
            cached = cur.execute("SELECT payload FROM cache WHERE user_prompt=:user__prompt AND system_prompt IS NULL",
                                 {"user_prompt" : user_prompt})
        else:
            cached = cur.execute("SELECT payload FROM cache WHERE user_prompt=:user_prompt AND system_prompt=:system_prompt",
                                 {"user_prompt" : user_prompt,
                                  "system_prompt": system_prompt})
        payload = cached.fetchone()
        if payload:
            prompt_peek = str(prompt)[0:80].replace("\n", "\\n")
            logger.info(f"Using cached payload for prompt: {prompt_peek}...")
            return payload[0]
        try:
            if system_prompt is None:
                responses = self.llama.chat_completion(
                    [{"role": "user", "content": user_prompt}],
                    max_gen_len=max_gen_len,
                    temperature=temperature,
                    top_p=top_p,
                )
            else:
                responses = self.llama.chat_completion(
                    [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}],
                    max_gen_len=max_gen_len,
                    temperature=temperature,
                    top_p=top_p,
                )
        except ValueError as e:
            logging.error(e)
            responses = []

        if len(responses) > 0:
            payload = responses[0]['generation']
            logger.info(f"Storing paylod of len: {len(payload)}")
            cur.execute("INSERT INTO cache (user_prompt, system_prompt, payload) VALUES (:user_prompt, :system_prompt, :payload)",
                        {"user_prompt": user_prompt,
                         "system_prompt": system_prompt,
                         "payload": payload})
            cur.connection.commit()
            return payload

        return ""

    def cached_completions(
            self, search_term: str = None) -> Iterator[Tuple[str, str]]:
        if search_term:
            search_term = search_term.lower()
        cur = self.db_cursor()
        responses = cur.execute("SELECT user_prompt, payload, system_prompt FROM cache")
        for row in respones:
            if (search_term
                    and search_term not in row[0].lower()
                    and search_term not in row[1].lower()):
                continue
            yield row

    def get_tokenizer(self, model=""):
        return self.llama.tokenizer
