"""Tiny logging helper so every module logs in a consistent way."""
from __future__ import annotations

import logging
import os

_LEVEL = os.environ.get("OUTBOUND_COPILOT_LOG_LEVEL", "INFO").upper()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, _LEVEL, logging.INFO))
        logger.propagate = False
    return logger
