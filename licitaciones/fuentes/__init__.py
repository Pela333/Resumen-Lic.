"""Carga todas las fuentes disponibles para que queden registradas."""

from . import (  # noqa: F401
    acumar,
    agp,
    aubasa,
    ausa,
    ausol,
    ba_obras,
    bac,
    comirec,
    comprar,
    contratar,
    corredores_viales,
    habitat,
    minfra,
    opisu,
    pbac,
    vialidad,
)
from .base import REGISTRO, EstructuraCambiada, Fuente

__all__ = ["REGISTRO", "EstructuraCambiada", "Fuente"]


