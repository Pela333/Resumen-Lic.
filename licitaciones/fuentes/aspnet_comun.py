"""Funciones auxiliares comunes para la familia de portales ASP.NET (Compras Estatales).

Comparten la misma arquitectura de formularios WebForms, tablas GridListaPliegos,
formatos de fecha y resolución de enlaces de pliego mediante __doPostBack.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests

_log = logging.getLogger(__name__)

TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

_MESES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

from ..filtro import (
    PATRON_EXCLUSION,
    PATRON_OBRA,
    cumple_filtro_monto,
    es_de_obra_o_arquitectura,
    parsear_monto_pesos,
)

EXCLUSIONES_GENERALES = PATRON_EXCLUSION


def fecha_hoy_arg() -> date:
    """Devuelve la fecha actual en la zona horaria de Argentina."""
    return datetime.now(TZ_ARG).date()


def parsear_fecha_apertura(texto: str) -> date | None:
    """Extrae la fecha de apertura de formatos '12/11/2026', '5-11-26' o '12 de noviembre de 2026'."""
    if not texto:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto)
    if m:
        try:
            dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if anio < 100:
                anio += 2000
            return date(anio, mes, dia)
        except ValueError:
            pass

    m_es = re.search(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|sep?tiembre|octubre|noviembre|diciembre)\s+(?:de(?:l)?\s+)?(\d{4})\b",
        texto,
        re.IGNORECASE,
    )
    if m_es:
        try:
            dia = int(m_es.group(1))
            mes = _MESES_ES[m_es.group(2).lower()]
            anio = int(m_es.group(3))
            return date(anio, mes, dia)
        except (ValueError, KeyError):
            pass

    return None




def resolver_link_pliego(
    session: requests.Session,
    url_lista: str,
    target_postback: str,
    viewstate: str,
    viewstategen: str,
    eventval: str = "",
    timeout: int = 8,
) -> str | None:
    """Simula el doPostBack del enlace del proceso para obtener la URL directa del pliego ciudadano."""
    try:
        post_data = {
            "__EVENTTARGET": target_postback,
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
        }
        if eventval:
            post_data["__EVENTVALIDATION"] = eventval
        resp = session.post(url_lista, data=post_data, allow_redirects=False, timeout=timeout)
        loc = resp.headers.get("Location")
        if loc:
            if loc.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(url_lista)
                return f"{parsed.scheme}://{parsed.netloc}{loc}"
            return loc
    except Exception as exc:
        _log.debug("No se pudo resolver el pliego por postback en %s: %s", target_postback, exc)
    return None
