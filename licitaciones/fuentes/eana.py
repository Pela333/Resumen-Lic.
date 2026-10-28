"""Fuente: EANA - Empresa Argentina de Navegación Aérea.

Monitorea licitaciones públicas, privadas y contrataciones abreviadas de infraestructura
aeronáutica, torres de control, radioayudas y obras civiles en aeropuertos.
URL Oficial: https://www.eana.com.ar/licitaciones
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
class Eana(Fuente):
    clave = "eana"
    nombre = "EANA - Navegación Aérea Argentina"
    url = "https://www.eana.com.ar/licitaciones"

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
            raise EstructuraCambiada(f"Error conectando con EANA: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        views = soup.find_all(class_="view-content")
        if not views:
            raise EstructuraCambiada("No se encontró 'view-content' en la página de EANA.")

        resultados: list[Licitacion] = []

        for vc in views:
            for row in vc.find_all(class_="views-row"):
                txt = row.get_text(" | ", strip=True)
                if "día y hora de apertura" not in txt.lower() and "objeto:" not in txt.lower():
                    continue

                partes = [p.strip() for p in txt.split("|") if p.strip()]
                numero = partes[0] if partes else "Licitación EANA"

                m_ap = re.search(r"D[ií]a y hora de apertura:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
                ap_str = m_ap.group(1).strip() if m_ap else ""

                m_obj = re.search(r"Objeto:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
                objeto = m_obj.group(1).strip() if m_obj else txt[:120]

                m_f = re.search(r"(\d{2})/(\d{2})/(\d{4})", ap_str)
                if not m_f:
                    continue
                try:
                    f_dt = datetime(int(m_f.group(3)), int(m_f.group(2)), int(m_f.group(1))).date()
                except ValueError:
                    continue

                if f_dt < hoy:
                    continue

                if not es_de_obra_o_arquitectura(objeto):
                    continue

                a_tag = row.find("a", href=True)
                link = self.url
                if a_tag:
                    h = a_tag["href"]
                    link = f"https://www.eana.com.ar{h}" if h.startswith("/") else h

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=numero,
                        organismo=self.nombre,
                        numero=numero,
                        objeto=objeto,
                        link=link,
                        presupuesto_oficial=NO_INFORMADO,
                        apertura=ap_str,
                    )
                )

        return resultados
