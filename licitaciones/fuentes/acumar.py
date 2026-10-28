"""Fuente: ACUMAR - Autoridad de Cuenca Matanza Riachuelo.

Monitorea compras y contrataciones de obras hidráulicas, saneamiento,
recuperación ambiental y mantenimiento en la Cuenca Matanza Riachuelo.
URL Oficial: https://www.acumar.gob.ar/transparencia/compras-y-contrataciones/
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
class Acumar(Fuente):
    clave = "acumar"
    nombre = "ACUMAR - Cuenca Matanza Riachuelo"
    url = "https://www.acumar.gob.ar/transparencia/compras-y-contrataciones/"

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
            raise EstructuraCambiada(f"Error conectando con ACUMAR: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        tabla = soup.find("table")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla de contrataciones en ACUMAR.")

        filas = tabla.find_all("tr")[1:]
        if not filas:
            raise EstructuraCambiada("La tabla de contrataciones de ACUMAR vino sin filas.")

        resultados: list[Licitacion] = []

        for tr in filas:
            celdas = [c.get_text(strip=True) for c in tr.find_all("td")]
            if len(celdas) < 6:
                continue

            proceso_raw, objeto, tipo, f_str, hora, estado = celdas[:6]

            # Extraer identificador de proceso (limpiando textos de pliegos adjuntos si vinieran pegados)
            m_proc = re.search(r"(\d+-\d+-[A-Z0-9]+)", proceso_raw)
            numero = m_proc.group(1) if m_proc else proceso_raw[:30]

            m_f = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", f_str)
            if not m_f:
                continue

            dia, mes, anio = int(m_f.group(1)), int(m_f.group(2)), int(m_f.group(3))
            try:
                f_dt = datetime(anio, mes, dia).date()
            except ValueError:
                try:
                    f_dt = datetime(anio, dia, mes).date()
                except ValueError:
                    continue

            if f_dt < hoy:
                continue

            if not es_de_obra_o_arquitectura(objeto):
                continue

            a_tag = tr.find("a", href=True)
            link = a_tag["href"] if a_tag else self.url

            apertura_completa = f"{f_str} {hora}".strip() if hora else f_str

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto,
                    link=link,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura=apertura_completa,
                    extra={"Tipo de Proceso": tipo, "Estado": estado},
                )
            )

        return resultados
