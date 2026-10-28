"""Fuente: GCBA - Corporación Buenos Aires Sur / Licitaciones Públicas GCABA.

Monitorea la sección de licitaciones públicas 2026 de GCABA con tolerancia a
intermitencias (HTTP 503 / ReadTimeout) del servidor histórico de buenosaires.gob.ar.
URL Oficial: https://buenosaires.gob.ar/gcaba_historico/licitaciones-en-curso/licitaciones-publicas-2026
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class CorporacionSur(Fuente):
    clave = "corporacion_sur"
    nombre = "GCBA - Licitaciones Públicas / Corporación Sur"
    url = "https://buenosaires.gob.ar/gcaba_historico/licitaciones-en-curso/licitaciones-publicas-2026"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        import requests
        sesion = requests.Session()

        try:
            resp = sesion.get(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=6,
                verify=False,
            )
            if resp.status_code >= 500:
                _log.warning("Servidor GCBA Histórico devolvió HTTP %s; se asume sin novedades.", resp.status_code)
                return []
            resp.raise_for_status()
        except Exception as exc:
            _log.warning("Timeout/intermitencia en GCBA Histórico (%s); se omite sin alerta falsa.", exc)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        main = soup.find("main") or soup.find("article") or soup

        if "no hay licitaciones" in main.get_text(" ", strip=True).lower():
            return []

        resultados: list[Licitacion] = []
        for a in main.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            href = a["href"].strip()
            if not re.search(r"licitaci[óo]n", txt, re.IGNORECASE):
                continue
            if not es_de_obra_o_arquitectura(txt):
                continue
            f_dt = parsear_fecha_apertura(txt)
            if not f_dt or f_dt < hoy:
                continue
            link_full = href if href.startswith("http") else f"https://buenosaires.gob.ar{href}"
            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=re.sub(r"[^a-zA-Z0-9_-]", "_", txt[:60]),
                    organismo=self.nombre,
                    numero=txt[:50],
                    objeto=txt,
                    link=link_full,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura=f_dt.strftime("%d/%m/%Y"),
                )
            )

        return resultados
