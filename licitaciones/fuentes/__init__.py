"""Carga todas las fuentes disponibles para que queden registradas."""

from . import (  # noqa: F401
    acumar,
    agp,
    ambiente_nacion,
    aubasa,
    ausa,
    ausol,
    aysa,
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
    proinged,
    puerto_la_plata,
    senado,
    vialidad,
)
from .base import REGISTRO, EstructuraCambiada, Fuente

__all__ = ["REGISTRO", "EstructuraCambiada", "Fuente"]


