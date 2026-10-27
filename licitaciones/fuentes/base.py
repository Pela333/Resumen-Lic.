"""Base común para todas las fuentes (patrón de "enchufes").

Para sumar un organismo nuevo se crea un archivo en esta carpeta con una clase
que herede de `Fuente`, se la decora con `@registrar` y se agrega su clave
en `config.toml > [fuentes] activas`. Nada más del sistema cambia.

Las fuentes simples usan `self.web` (HTTP directo). Las complejas
(JavaScript, varias pantallas, login) podrán usar un navegador automatizado
o una API interna, sin afectar a las demás.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..modelo import Licitacion
from ..web import ClienteWeb


class EstructuraCambiada(Exception):
    """La página respondió, pero no tiene la forma esperada (probable rediseño)."""


class Fuente(ABC):
    clave: str = ""
    nombre: str = ""
    url: str = ""

    def __init__(self, web: ClienteWeb) -> None:
        self.web = web

    @abstractmethod
    def recolectar(self) -> list[Licitacion]:
        """Devuelve todas las licitaciones visibles hoy en la fuente."""


REGISTRO: dict[str, type[Fuente]] = {}


def registrar(cls: type[Fuente]) -> type[Fuente]:
    REGISTRO[cls.clave] = cls
    return cls
