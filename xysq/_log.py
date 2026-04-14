"""Structured logging under the 'xysq' namespace."""

import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"xysq.{name}")
