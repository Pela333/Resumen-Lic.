"""Fuente: Puerto La Plata - Consorcio de Gestión del Puerto La Plata.

Monitorea licitaciones de dragado, mantenimiento de muelles, infraestructura
y obras civiles en el ámbito del Puerto de La Plata, Berisso y Ensenada.
URL Oficial: https://puertolaplata.com/servicios-y-negocios/licitaciones-publicadas
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class PuertoLaPlata(Fuente):
    clave = "puerto_la_plata"
    nombre = "Puerto La Plata - Consorcio de Gestión"
    url = "https://puertolaplata.com/servicios-y-negocios/licitaciones-publicadas"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con Puerto La Plata: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        texto_pagina = soup.get_text()

        # Si el sitio informa explícitamente que no hay licitaciones en este momento:
        if "no hay licitaciones publicadas" in texto_pagina.lower():
            return []

        # Si hay publicaciones o tablas
        tabla = soup.find("table")
        items = soup.find_all(class_=lambda x: x and any(c in x.lower() for c in ["licitacion", "item", "card"]))

        if not tabla and not items:
            raise EstructuraCambiada("No se reconoció la estructura de listado en Puerto La Plata.")

        resultados: list[Licitacion] = []
        # Parsea filas de tabla si existen
        if tabla:
            for tr in tabla.find_all("tr")[1:]:
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(tds) < 3:
                    continue
                objeto = tds[1] if len(tds) > 1 else tds[0]
                numero = tds[0]
                a_tag = tr.find("a", href=True)
                link = a_tag["href"] if a_tag else self.url
                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=numero,
                        organismo=self.nombre,
                        numero=numero,
                        objeto=objeto,
                        link=link,
                        presupuesto_oficial=NO_INFORMADO,
                        apertura=NO_INFORMADO,
                    )
                )

        return resultados
