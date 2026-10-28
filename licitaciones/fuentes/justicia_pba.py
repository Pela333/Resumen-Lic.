"""Fuente: Ministerio de Justicia y Derechos Humanos PBA.

Monitorea licitaciones de infraestructura penitenciaria, alcaidías, unidades
carcelarias y edificios judiciales en la Provincia de Buenos Aires.
URL Oficial: https://www.gba.gob.ar/justicia_y_ddhh/licitaciones
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class JusticiaPba(Fuente):
    clave = "justicia_pba"
    nombre = "Ministerio de Justicia y DDHH PBA"
    url = "https://www.gba.gob.ar/justicia_y_ddhh/licitaciones"

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
            raise EstructuraCambiada(f"Error conectando con Justicia PBA: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        if "justicia y derechos humanos" not in soup.get_text().lower():
            raise EstructuraCambiada("No se reconoció el portal de Justicia y DDHH PBA.")

        reg = soup.find(class_="region-content")
        if not reg:
            return []

        resultados: list[Licitacion] = []
        for a in reg.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            href = a["href"]
            if "licitaci" in txt.lower() or "obra" in txt.lower():
                m_f = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
                if m_f:
                    try:
                        f_dt = datetime(int(m_f.group(3)), int(m_f.group(2)), int(m_f.group(1))).date()
                        if f_dt < hoy:
                            continue
                    except ValueError:
                        pass
                link = f"https://www.gba.gob.ar{href}" if href.startswith("/") else href
                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=href,
                        organismo=self.nombre,
                        numero=txt[:30],
                        objeto=txt,
                        link=link,
                        presupuesto_oficial=NO_INFORMADO,
                        apertura=NO_INFORMADO,
                    )
                )

        return resultados
