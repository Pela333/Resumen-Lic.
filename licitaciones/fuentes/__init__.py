"""Carga todas las fuentes disponibles para que queden registradas."""

from . import aubasa, ausa, ausol, ba_obras, bac, comprar, contratar, pbac, vialidad  # noqa: F401
from .base import REGISTRO, EstructuraCambiada, Fuente

__all__ = ["REGISTRO", "EstructuraCambiada", "Fuente"]

