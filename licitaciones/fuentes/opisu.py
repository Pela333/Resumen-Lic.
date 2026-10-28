"""Fuente: OPISU - Organismo Provincial de Integración Social y Urbana (PBA).

Monitorea las licitaciones públicas de obras de hábitat, saneamiento, infraestructura
y equipamiento comunitario en barrios populares de la Provincia de Buenos Aires.
URL Oficial: https://www.gba.gob.ar/opisu/licitaciones_en_curso_de_obras
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from ..modelo import Licitacion
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class Opisu(Fuente):
    clave = "opisu"
    nombre = "OPISU - Integración Social y Urbana PBA"
    url = "https://adquisiciones.opisu.gba.gob.ar/obras"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        secciones = [
            ("Obras", "https://adquisiciones.opisu.gba.gob.ar/obras"),
            ("Bienes y Servicios", "https://adquisiciones.opisu.gba.gob.ar/bienes"),
        ]

        resultados: list[Licitacion] = []
        filas_leidas = 0

        for etiqueta_rubro, url_seccion in secciones:
            try:
                resp = sesion.get(url_seccion, timeout=self.web.timeout)
                resp.raise_for_status()
            except Exception as exc:
                _log.warning("No se pudo conectar con %s: %s", url_seccion, exc)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            tabla = soup.find("table")
            if not tabla:
                continue

            filas = tabla.find("tbody").find_all("tr") if tabla.find("tbody") else tabla.find_all("tr")[1:]

            for tr in filas:
                celdas = [c.get_text(strip=True) for c in tr.find_all("td")]
                if len(celdas) < 6:
                    continue
                filas_leidas += 1

                objeto = celdas[0]
                expediente = celdas[1]
                comitente = celdas[2]
                municipio = celdas[3]
                fecha_str = celdas[4]
                estado = celdas[5]
                proc = celdas[6] if len(celdas) > 6 else ""

                if any(e in estado.lower() for e in ["adjudicad", "finalizad", "desiert", "fracasad", "cancelad"]):
                    continue

                m = re.search(r"(\d{2})/(\d{2})/(\d{4})", fecha_str)
                if not m:
                    continue
                try:
                    f_dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
                except ValueError:
                    continue

                if f_dt < hoy:
                    continue

                a_tag = tr.find("a")
                link = url_seccion
                if a_tag and a_tag.get("href"):
                    h = a_tag["href"]
                    link = f"https://adquisiciones.opisu.gba.gob.ar/{h.lstrip('/')}" if not h.startswith("http") else h

                numero = proc if proc else expediente
                id_fuente = expediente if expediente else numero

                organismo = f"OPISU ({etiqueta_rubro}) - {municipio}" if municipio else f"OPISU ({etiqueta_rubro})"

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=id_fuente,
                        organismo=organismo,
                        numero=numero,
                        objeto=objeto,
                        link=link,
                        apertura=fecha_str,
                        extra={"Estado": estado, "Municipio": municipio, "Comitente": comitente},
                    )
                )

        if filas_leidas == 0:
            raise EstructuraCambiada("No se pudo acceder o leer ninguna fila de las tablas de OPISU.")

        return resultados
