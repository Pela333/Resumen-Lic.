"""Carga todas las fuentes disponibles para que queden registradas."""

from . import aubasa, ausa, ausol, vialidad  # noqa: F401
from .base import REGISTRO, EstructuraCambiada, Fuente

__all__ = ["REGISTRO", "EstructuraCambiada", "Fuente"]
