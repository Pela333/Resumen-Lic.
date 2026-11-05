"""Formato único de licitación.

Cada fuente, sin importar cómo sea su página, entrega objetos de este tipo.
Así el resto del sistema (base de datos, PDF, mail) no necesita saber de dónde vino cada dato.

Regla de precisión: los textos se guardan tal cual aparecen en la fuente.
Nunca se calculan, convierten ni redondean montos o fechas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

NO_INFORMADO = "No informado en la web"


@dataclass
class Licitacion:
    fuente: str              # clave interna de la fuente, ej. "aubasa"
    id_fuente: str           # identificador estable dentro de esa fuente
    organismo: str
    numero: str              # número de licitación / expediente, tal cual figura
    objeto: str
    link: str                # enlace a la publicación o documentación oficial
    presupuesto_oficial: str = NO_INFORMADO
    recepcion_ofertas: str = NO_INFORMADO
    apertura: str = NO_INFORMADO
    valor_pliego: str = NO_INFORMADO
    lugar_consulta: str = NO_INFORMADO
    extra: dict[str, str] = field(default_factory=dict)  # campos que la fuente publica y no mapeamos

    @property
    def uid(self) -> str:
        """Identificador único global, usado para no repetir envíos."""
        return f"{self.fuente}:{self.id_fuente}"

    @property
    def firma(self) -> str:
        """Huella de contenido (objeto + fecha de apertura), independiente de la fuente y de la edición.

        Sirve para detectar la misma licitación publicada en varias ediciones del boletín
        o en más de un portal.
        """
        return f"{_normalizar(self.objeto)[:150]}|{_fecha_clave(self.apertura)}"

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos: dict) -> "Licitacion":
        return cls(**datos)


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", sin_tildes.lower())


_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
          "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _fecha_clave(texto: str) -> str:
    """Devuelve la fecha del texto como AAAA-MM-DD (o el texto normalizado si no se reconoce)."""
    t = (texto or "").lower()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{1,2})\D{0,4}\s+de\s+([a-z]+)\s+de\s+(\d{4})", t)
    if m and m.group(2) in _MESES:
        return f"{m.group(3)}-{_MESES[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return _normalizar(texto)[:20]


def _tiene_presupuesto(lic: "Licitacion") -> bool:
    return bool(re.search(r"\d", lic.presupuesto_oficial or ""))


def son_la_misma(a: "Licitacion", b: "Licitacion") -> bool:
    """True si a y b describen la misma licitación."""
    if a.firma != b.firma or len(_normalizar(a.objeto)) < 8:
        return False
    if a.fuente != b.fuente:
        return True  # mismo texto y fecha en portales distintos (p. ej. BAC y BOCBA)
    # dentro de una misma fuente se exige además el mismo organismo (o el mismo presupuesto informado)
    if _normalizar(a.organismo) == _normalizar(b.organismo):
        return True
    return _tiene_presupuesto(a) and _normalizar(a.presupuesto_oficial) == _normalizar(b.presupuesto_oficial)


def deduplicar(licitaciones: list["Licitacion"], ya_vistas: list["Licitacion"] | None = None):
    """Separa (únicas, duplicadas). Se queda con la versión más completa (la que informa presupuesto).

    `ya_vistas` son licitaciones ya enviadas antes: si una nueva coincide con alguna, es duplicada.
    """
    ya_vistas = ya_vistas or []
    ordenadas = sorted(licitaciones, key=lambda l: (not _tiene_presupuesto(l)))
    unicas: list[Licitacion] = []
    duplicadas: list[Licitacion] = []
    for lic in ordenadas:
        if any(son_la_misma(lic, otra) for otra in ya_vistas) or any(son_la_misma(lic, u) for u in unicas):
            duplicadas.append(lic)
        else:
            unicas.append(lic)
    orden = {id(l): i for i, l in enumerate(licitaciones)}
    unicas.sort(key=lambda l: orden[id(l)])
    return unicas, duplicadas
