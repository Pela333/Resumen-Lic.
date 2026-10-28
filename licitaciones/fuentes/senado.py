"""Fuente: Senado de la Nación Argentina - Dirección General de Administración.

Monitorea las licitaciones públicas, privadas y contrataciones directas
para mantenimiento de edificios históricos, obras de infraestructura y servicios del Senado.
URL Oficial: https://www.senado.gob.ar/administrativo/Licitaciones
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
class Senado(Fuente):
    clave = "senado"
    nombre = "Senado de la Nación Argentina"
    url = "https://www.senado.gob.ar/administrativo/Licitaciones"

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
            raise EstructuraCambiada(f"Error conectando con Senado de la Nación: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        tabla = soup.find("table")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla de licitaciones en el Senado de la Nación.")

        filas = tabla.find_all("tr")[1:]
        if not filas:
            raise EstructuraCambiada("La tabla de licitaciones del Senado vino sin filas.")

        resultados: list[Licitacion] = []

        for tr in filas:
            celdas = [c.get_text(strip=True) for c in tr.find_all("td")]
            if len(celdas) < 3:
                continue

            f_raw, exp_raw, objeto = celdas[:3]

            m_f = re.search(r"(\d{2})-(\d{2})-(\d{4})", f_raw)
            if not m_f:
                continue

            dia, mes, anio = int(m_f.group(1)), int(m_f.group(2)), int(m_f.group(3))
            try:
                f_dt = datetime(anio, mes, dia).date()
            except ValueError:
                continue

            if f_dt < hoy:
                continue

            if not es_de_obra_o_arquitectura(objeto):
                continue

            m_exp = re.search(r"([A-Z0-9\-]+/\d{4})", exp_raw)
            expediente = m_exp.group(1) if m_exp else exp_raw[:25]

            a_tag = tr.find("a", href=True)
            link = self.url
            if a_tag:
                h = a_tag["href"]
                link = f"https://www.senado.gob.ar{h}" if h.startswith("/") else h

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=expediente,
                    organismo=self.nombre,
                    numero=expediente,
                    objeto=objeto,
                    link=link,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura=f"{dia:02d}/{mes:02d}/{anio:04d}",
                )
            )

        return resultados
