"""Fuente: Dirección General de Cultura y Educación PBA (DGCyE / ABC) - Infraestructura Escolar.

Conecta mediante un adaptador SSL con soporte para cifrado legado (SECLEVEL=1) requerido
por el servidor abc2.abc.gob.ar y extrae las contrataciones de Obra Pública vigentes.
URL Oficial: https://abc2.abc.gob.ar/area_administrativa
"""

from __future__ import annotations

import logging
import re
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


class _LegacySSLAdapter(HTTPAdapter):
    """Permite negociar claves DH heredadas en abc2.abc.gob.ar sin fallar con DH_KEY_TOO_SMALL."""

    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        self.poolmanager = urllib3.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
        )


@registrar
class DgcyePba(Fuente):
    clave = "dgcye_pba"
    nombre = "DGCyE PBA - Infraestructura Escolar (ABC)"
    url = "https://abc2.abc.gob.ar/area_administrativa"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = requests.Session()
        sesion.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )
        sesion.mount("https://", _LegacySSLAdapter())

        try:
            resp = sesion.get(self.url, timeout=self.web.timeout, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con DGCyE ABC ({self.url}): {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        filas = soup.select(".views-row")
        if not filas:
            raise EstructuraCambiada("No se encontraron bloques .views-row en DGCyE ABC.")

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for fila in filas:
            texto_fila = fila.get_text(" | ", strip=True)
            if not texto_fila:
                continue

            def _campo(selector: str) -> str:
                el = fila.select_one(selector)
                return el.get_text(" ", strip=True) if el else ""

            procedimiento = _campo(".views-field-field-concurso-nro .field-content")
            expediente = _campo(".views-field-title .field-content")
            distrito = _campo(".views-field-field-obra-publica-distrito .field-content")
            escuela = _campo(".views-field-field-escuela .field-content")
            caratula = _campo(".views-field-field-car-tula .field-content")
            monto = _campo(".views-field-field-monto .field-content")
            apertura_raw = _campo(".views-field-field-fecha-hora-lugar-de-apertu .field-content")

            if not apertura_raw:
                m_ap = re.search(r"Fecha\s*de\s*Apertura:\s*([^|]+)", texto_fila, re.IGNORECASE)
                apertura_raw = m_ap.group(1).strip() if m_ap else ""

            if not apertura_raw:
                continue

            f_dt = parsear_fecha_apertura(apertura_raw)
            if not f_dt or f_dt < hoy:
                continue

            partes_obj = [p for p in (caratula, escuela, distrito) if p]
            objeto = " - ".join(partes_obj) if partes_obj else texto_fila[:200]
            if not caratula and not es_de_obra_o_arquitectura(objeto):
                continue

            numero = procedimiento or expediente or f"DGCYE-{len(resultados) + 1}"
            id_fuente = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{numero}_{expediente}")[:80]
            if id_fuente in vistos:
                continue
            vistos.add(id_fuente)

            link_doc = self.url
            a_pdf = fila.select_one("a[href*='.pdf'], a[href*='.rar'], a[href*='.zip']")
            if a_pdf and a_pdf.get("href"):
                href = a_pdf["href"].strip()
                link_doc = href if href.startswith("http") else f"https://abc2.abc.gob.ar{href}"

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_fuente,
                    organismo=f"{self.nombre} ({distrito})" if distrito else self.nombre,
                    numero=f"{procedimiento} ({expediente})" if (procedimiento and expediente) else numero,
                    objeto=objeto,
                    link=link_doc,
                    presupuesto_oficial=monto if monto else NO_INFORMADO,
                    apertura=apertura_raw,
                )
            )

        return resultados
