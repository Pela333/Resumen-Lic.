"""Fuente: AGP - Administración General de Puertos S.E.

Monitorea licitaciones de obras portuarias, dragado, balizamiento,
mantenimiento y adecuación de muelles y sectores de la Vía Navegable Troncal.
URL Oficial: https://www.agpsau.gob.ar/llamados/82
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
class Agp(Fuente):
    clave = "agp"
    nombre = "AGP - Administración General de Puertos"
    url = "https://www.agpsau.gob.ar/llamados/82"

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
            raise EstructuraCambiada(f"Error conectando con AGP: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        boxes = soup.find_all(class_="box-listado")
        if not boxes:
            raise EstructuraCambiada("No se encontraron elementos 'box-listado' en AGP.")

        resultados: list[Licitacion] = []

        for b in boxes:
            txt = b.get_text(" | ", strip=True)
            m_num = re.search(r"N[uú]mero de licitaci[oó]n:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
            m_obj = re.search(r"Objeto:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
            m_ap = re.search(r"D[ií]a y Hora de Apertura:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
            m_tipo = re.search(r"Tipo de Licitaci[oó]n:\s*\|\s*([^|]+)", txt, re.IGNORECASE)
            m_pres = re.search(r"Presupuesto Oficial:\s*\|\s*([^|]+)", txt, re.IGNORECASE)

            num = m_num.group(1).strip() if m_num else "S/N"
            obj = m_obj.group(1).strip() if m_obj else ""
            ap_str = m_ap.group(1).strip() if m_ap else ""
            tipo = m_tipo.group(1).strip() if m_tipo else "Licitación"
            pres = m_pres.group(1).strip() if m_pres else NO_INFORMADO

            m_f = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", ap_str)
            if not m_f:
                continue

            try:
                f_dt = datetime(int(m_f.group(3)), int(m_f.group(2)), int(m_f.group(1))).date()
            except ValueError:
                continue

            if f_dt < hoy:
                continue

            if not es_de_obra_o_arquitectura(obj):
                continue

            # Encontrar primer enlace a pliego o carátula si existe
            a_link = b.find("a", href=lambda h: h and "/descargar_licitacion/" in h)
            link = f"https://www.agpsau.gob.ar{a_link['href']}" if a_link and a_link["href"].startswith("/") else (a_link["href"] if a_link else self.url)

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=num,
                    organismo=self.nombre,
                    numero=f"{tipo} N° {num}",
                    objeto=obj,
                    link=link,
                    presupuesto_oficial=pres,
                    apertura=ap_str,
                    extra={"Tipo de Proceso": tipo},
                )
            )

        return resultados
