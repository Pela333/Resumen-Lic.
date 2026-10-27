"""Fuente: AUBASA - Autopistas de Buenos Aires S.A.

Estructura observada el 27/10/2026 en https://compras.aubasa.com.ar/ :
- Página HTML simple (sin JavaScript para los datos).
- Dentro de <div class="cuerpo-licitaciones"> hay una <table class="table-striped"> por licitación.
  - El encabezado <th> tiene el número: "LICITACIÓN PÚBLICA Nº12/2026".
  - Cada fila <td> tiene una etiqueta en <strong> ("Objeto", "Valor del Pliego:", etc.) y debajo el valor.
- Después de cada tabla hay un enlace "Descargar documentación" a /show/<número>.
  Ese número se usa como identificador estable.
- No publica presupuesto oficial ni fecha de publicación en la web.
"""

from __future__ import annotations

import re
import unicodedata

from bs4 import Tag

from ..modelo import Licitacion
from .base import EstructuraCambiada, Fuente, registrar

ENLACE_DOC = re.compile(r"/show/(\d+)")

# Etiqueta en la web (normalizada, sin acentos) -> campo del modelo
ETIQUETAS = {
    "objeto": "objeto",
    "lugar de consulta": "lugar_consulta",
    "valor del pliego": "valor_pliego",
    "recepcion de ofertas": "recepcion_ofertas",
    "acto de apertura": "apertura",
    "presupuesto": "presupuesto_oficial",
}


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_acentos).strip(" :").lower()


def _limpio(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


@registrar
class Aubasa(Fuente):
    clave = "aubasa"
    nombre = "AUBASA - Autopistas de Buenos Aires S.A."
    url = "https://compras.aubasa.com.ar/"

    def recolectar(self) -> list[Licitacion]:
        pagina = self.web.html(self.url)

        if pagina.select_one("div.cuerpo-licitaciones") is None:
            raise EstructuraCambiada("No se encontró el bloque 'cuerpo-licitaciones' en la página.")

        # Tablas y enlaces en orden de aparición: cada enlace pertenece a la última tabla vista.
        elementos = pagina.find_all(
            lambda t: (t.name == "table" and "table-striped" in (t.get("class") or []))
            or (t.name == "a" and ENLACE_DOC.search(t.get("href") or ""))
        )

        resultados: list[Licitacion] = []
        actual: Licitacion | None = None
        for el in elementos:
            if el.name == "table":
                actual = self._leer_tabla(el)
                resultados.append(actual)
            elif actual is not None and actual.link == self.url:
                href = el["href"]
                actual.link = href
                actual.id_fuente = ENLACE_DOC.search(href).group(1)
        return resultados

    def _leer_tabla(self, tabla: Tag) -> Licitacion:
        encabezado = tabla.find("th")
        if encabezado is None:
            raise EstructuraCambiada("Una tabla de licitación no tiene encabezado con el número.")
        numero = _limpio(encabezado.get_text(" "))

        campos: dict[str, str] = {}
        extra: dict[str, str] = {}
        for celda in tabla.find_all("td"):
            etiqueta_tag = celda.find("strong")
            if etiqueta_tag is None:
                continue
            etiqueta = _limpio(etiqueta_tag.get_text(" "))
            etiqueta_tag.extract()
            valor = _limpio(celda.get_text(" "))
            clave = next((campo for k, campo in ETIQUETAS.items() if _normalizar(etiqueta).startswith(k)), None)
            if clave:
                campos[clave] = valor
            else:
                extra[etiqueta.strip(" :")] = valor

        if not campos.get("objeto"):
            raise EstructuraCambiada(f"La licitación '{numero}' no tiene el campo 'Objeto'.")

        # Identificador provisorio por número; se reemplaza por el de /show/ si existe el enlace.
        id_provisorio = re.sub(r"[^a-z0-9]+", "-", _normalizar(numero)).strip("-")
        return Licitacion(
            fuente=self.clave,
            id_fuente=id_provisorio,
            organismo=self.nombre,
            numero=numero,
            link=self.url,
            extra=extra,
            **campos,
        )
