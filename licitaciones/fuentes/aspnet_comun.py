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

# Vocabulario de obras viales, arquitectura, hidráulica, infraestructura y edificaciones
PATRON_OBRA = re.compile(
    r"\b("
    r"obra|obras|construcci[oó]n|construcciones|arquitectur[a-z]*|vial|viales|"
    r"paviment[a-z]*|asfalt[a-z]*|hormig[oó]n[a-z]*|bacheo|puente|puentes|camino|caminos|"
    r"rutas?|hidr[aá]ulic[a-z]*|desag[uü]es?|canal(?:es)?|drenaje|remodelaci[oó]n|remodelaciones|"
    r"refacci[oó]n|refacciones|alba[nñ]iler[ií]a|techad[a-z]*|cubiertas?|infraestructur[a-z]*|"
    r"demolici[oó]n|sanitari[a-z]*|gasoducto|cloac[a-z]*|acueducto|luminarias?|alumbrado|"
    r"electromec[aá]nic[a-z]*|se[nñ]alamiento|edifici[a-z]*|vivienda|viviendas|instalaci[oó]n|instalaciones"
    r")\b",
    re.IGNORECASE,
)

# Exclusiones específicas para portales generalistas (compras de insumos médicos, limpieza, alimentos, etc.)
EXCLUSIONES_GENERALES = re.compile(
    r"\b("
    r"pr[oó]tesis|medicament[a-z]*|f[aá]rmac[a-z]*|nutroter[a-z]*|cirug[ií]a|"
    r"laboratorio|reactiv[a-z]*|bistur[ií]|limpieza|c[aá]rnic[a-z]*|frutas?|verduras?|"
    r"vacunas?|descartables?|jeringas?|colch[oó]n[a-z]*|s[aá]banas?|alimentos?|plotter|"
    r"uniforme[a-z]*|resucitador|mam[oó]grafo|tom[oó]grafo"
    r")\b",
    re.IGNORECASE,
)


def fecha_hoy_arg() -> date:
    """Devuelve la fecha actual en la zona horaria de Argentina."""
    return datetime.now(TZ_ARG).date()


def parsear_fecha_apertura(texto: str) -> date | None:
    """Extrae la fecha de apertura de un string como '12/11/2026 13:00 Hrs.'."""
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto)
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
    except ValueError:
        return None


def es_de_obra_o_arquitectura(texto: str) -> bool:
    """Evalúa si el objeto de la licitación corresponde al rubro de construcción / arquitectura / viales."""
    if EXCLUSIONES_GENERALES.search(texto):
        return False
    return bool(PATRON_OBRA.search(texto))


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
                # Extrae el esquema y dominio de url_lista
                from urllib.parse import urlparse
                parsed = urlparse(url_lista)
                return f"{parsed.scheme}://{parsed.netloc}{loc}"
            return loc
    except Exception as exc:
        _log.debug("No se pudo resolver el pliego por postback en %s: %s", target_postback, exc)
    return None
