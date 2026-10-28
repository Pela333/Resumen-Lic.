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

# Vocabulario de obras viales, arquitectura, hidráulica, infraestructura y edificaciones
PATRON_OBRA = re.compile(
    r"\b("
    r"obra[s]?(?!\s+social)|construcci[oó]n|construcciones|arquitectur[a-z]*|vial|viales|"
    r"paviment[a-z]*|asfalt[a-z]*|hormig[oó]n[a-z]*|bacheo|puente|puentes|camino|caminos|"
    r"rutas?|hidr[aá]ulic[a-z]*|desag[uü]es?|canal(?:es)?|drenaje|remodelaci[oó]n|remodelaciones|"
    r"refacci[oó]n|refacciones|alba[nñ]iler[ií]a|techad[a-z]*|techo[s]?|cubiertas?|infraestructur[a-z]*|"
    r"demolici[oó]n|sanitari[a-z]*|gasoducto|cloac[a-z]*|acueducto|luminarias?|alumbrado|"
    r"electromec[aá]nic[a-z]*|termomec[aá]nic[a-z]*|se[nñ]alamiento|edilici[a-z]*|"
    r"mantenimiento de edifici[a-z]*|reparaci[oó]n de edifici[a-z]*|"
    r"vivienda|viviendas|adecuaci[oó]n|adecuaciones|readecuaci[oó]n|"
    r"impermeabiliz[a-z]*|mamposter[ií]a|pluvial[a-z]*|veredas?|calefacci[oó]n|aire[s]? acondicionado[s]?|"
    r"puesta en valor|pintura exterior|pintura interior|red el[eé]ctrica|sistema el[eé]ctrico|"
    r"instalaci[oó]n el[eé]ctrica|instalaciones el[eé]ctricas|instalaci[oó]n sanitaria|instalaci[oó]n de gas|"
    r"tablero[s]? el[eé]ctrico[s]?|grupo electr[oó]geno"
    r")\b",
    re.IGNORECASE,
)

# Exclusiones específicas para portales generalistas (compras de insumos médicos, limpieza, alimentos, muebles, etc.)
EXCLUSIONES_GENERALES = re.compile(
    r"\b("
    r"pr[oó]tesis|medicament[a-z]*|f[aá]rmac[a-z]*|nutroter[a-z]*|cirug[ií]a|"
    r"laboratorio|reactiv[a-z]*|bistur[ií]|limpieza|c[aá]rnic[a-z]*|frutas?|verduras?|"
    r"vacunas?|descartables?|jeringas?|colch[oó]n[a-z]*|s[aá]banas?|alimentos?|plotter|"
    r"uniforme[a-z]*|resucitador|mam[oó]grafo|tom[oó]grafo|ec[oó]grafo|odontol[oó]gic[a-z]*|"
    r"papel obra|mobiliario[s]?|impresora[s]?|cabezal|seguro[s]? contra|p[oó]liza|"
    r"transmisi[oó]n de datos|enlace de|bater[ií]as|gr[uú]as?|"
    r"adquisici[oó]n de equipos|adquisici[oó]n de aires|"
    r"adquisici[oó]n de membrana|adquisici[oó]n de elementos|adquisici[oó]n de materiales|adquisici[oó]n de insumos|"
    r"compra de materiales|compra de insumos|provisi[oó]n de materiales|licencia[s]? de software|"
    r"infraestructura tecnol[oó]gica|servicio de limpieza|servicio de vigilancia|servicio de seguridad|alquiler de"
    r")\b",
    re.IGNORECASE,
)


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
                from urllib.parse import urlparse
                parsed = urlparse(url_lista)
                return f"{parsed.scheme}://{parsed.netloc}{loc}"
            return loc
    except Exception as exc:
        _log.debug("No se pudo resolver el pliego por postback en %s: %s", target_postback, exc)
    return None
