"""Fuente: Universidad Nacional de La Plata (UNLP) - Licitaciones de Obras (SEDICI).

Consume el canal oficial RSS 2.0 del repositorio institucional de Licitaciones de Obras
de la Secretaría de Planeamiento, Obras y Servicios de la UNLP (handle 10915/69217),
evitando el bloqueo anti-bot Anubis (HTTP 418) de la vista /discover.
URL Oficial: https://sedici.unlp.edu.ar/handle/10915/69217
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

URL_RSS = "https://sedici.unlp.edu.ar/feed/rss_2.0/10915/69217"


@registrar
class SediciUnlp(Fuente):
    clave = "sedici_unlp"
    nombre = "UNLP - Secretaría de Obras y Planeamiento (SEDICI)"
    url = "https://sedici.unlp.edu.ar/handle/10915/69217"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                URL_RSS,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as exc:
            raise EstructuraCambiada(f"Error consultando RSS de Licitaciones UNLP ({URL_RSS}): {exc}") from exc

        items = root.findall(".//item")
        if not items:
            raise EstructuraCambiada("El feed RSS de SEDICI UNLP no devolvió elementos <item>.")

        resultados: list[Licitacion] = []

        for item in items:
            titulo = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or self.url).strip().replace(":80/", "/").replace("http://", "https://")
            desc_raw = html.unescape(item.findtext("description") or "")
            texto_desc = BeautifulSoup(desc_raw, "html.parser").get_text("\n", strip=True)

            def _extraer(etiqueta: str) -> str:
                m = re.search(rf"{etiqueta}\s*:\s*([^\n]+)", texto_desc, re.IGNORECASE)
                return re.sub(r"\s+", " ", m.group(1)).strip(" .-") if m else ""

            objeto = _extraer("Objeto") or titulo
            direccion = _extraer(r"Direcci[óo]n de la obra")
            presupuesto = _extraer("Presupuesto oficial") or NO_INFORMADO
            valor_pliego = _extraer("Compra y valor de legajos") or NO_INFORMADO
            consultas = _extraer("Consultas") or NO_INFORMADO
            apertura_raw = _extraer(r"Presentaci[óo]n de ofertas y acto de apertura")

            if not apertura_raw:
                continue

            f_dt = parsear_fecha_apertura(apertura_raw)
            if not f_dt or f_dt < hoy:
                continue

            m_num = re.search(r"(Licitaci[óo]n\s+no\.\s*[\d/]+)", titulo, re.IGNORECASE)
            numero = m_num.group(1).strip() if m_num else titulo[:50]
            id_fuente = link.rstrip("/").split("/")[-1]

            objeto_completo = f"{objeto} ({direccion})" if direccion else objeto

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_fuente,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto_completo,
                    link=link,
                    presupuesto_oficial=presupuesto,
                    apertura=apertura_raw,
                    valor_pliego=valor_pliego,
                    lugar_consulta=consultas,
                )
            )

        return resultados
