"""Formato único de licitación.

Cada fuente, sin importar cómo sea su página, entrega objetos de este tipo.
Así el resto del sistema (base de datos, PDF, mail) no necesita saber de dónde vino cada dato.

Regla de precisión: los textos se guardan tal cual aparecen en la fuente.
Nunca se calculan, convierten ni redondean montos o fechas.
"""

from __future__ import annotations

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

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos: dict) -> "Licitacion":
        return cls(**datos)
