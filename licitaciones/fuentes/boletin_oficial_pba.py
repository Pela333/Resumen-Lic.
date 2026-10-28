"""Fuente: Boletín Oficial de la Provincia de Buenos Aires (BOPBA) - Sección Oficial y 135 Municipios.

Consulta directamente el endpoint JSON diario de páginas indexadas
(/boletin/YYYY-MM-DD/paginas/OFICIAL) sin pasar por el buscador global pesado (/buscar),
combinando los fragmentos de 'licitacion' y 'apertura' por página (#page=N) en ~1 segundo por petición.
URL Oficial: https://boletinoficial.gba.gob.ar/
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


def _ultimos_dias_habiles(hoy: date, cantidad: int = 3) -> list[date]:
    dias: list[date] = []
    actual = hoy
    intentos = 0
    while len(dias) < cantidad and intentos < 10:
        if actual.weekday() < 5:
            dias.append(actual)
        actual -= timedelta(days=1)
        intentos += 1
    return dias


@registrar
class BoletinOficialPba(Fuente):
    clave = "boletin_oficial_pba"
    nombre = "Boletín Oficial PBA (Oficial y 135 Municipios)"
    url = "https://boletinoficial.gba.gob.ar/"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        dias_consulta = _ultimos_dias_habiles(hoy, cantidad=3)

        sesion = requests.Session()
        sesion.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

        paginas_fragmentos: dict[str, list[str]] = defaultdict(list)
        respuestas_ok = 0
        ultimo_error: Exception | None = None
        t_inicio = time.monotonic()

        for dia in dias_consulta:
            f_iso = dia.strftime("%Y-%m-%d")
            url_dia = f"https://boletinoficial.gba.gob.ar/boletin/{f_iso}/paginas/OFICIAL"
            for palabra in ("licitacion", "apertura"):
                for pnum in range(1, 6):
                    if time.monotonic() - t_inicio > 28:
                        break
                    try:
                        resp = sesion.get(
                            url_dia,
                            params={"q": palabra, "pageNumber": pnum},
                            timeout=(8, 18),
                            verify=False,
                        )
                        if resp.status_code != 200:
                            break
                        rj = resp.json()
                        respuestas_ok += 1
                        html_parts = rj.get("html") or []
                        if not html_parts:
                            break
                        sp = BeautifulSoup("".join(html_parts), "html.parser")
                        pages = sp.find_all("a", class_="page")
                        excerpts = sp.find_all("p", class_="excerpt")
                        if not pages:
                            break
                        for a, exc_p in zip(pages, excerpts):
                            href = a.get("href", "").strip()
                            if href:
                                paginas_fragmentos[href].append(exc_p.get_text(" ", strip=True))
                    except Exception as exc:
                        ultimo_error = exc
                        break

        if respuestas_ok == 0 and ultimo_error is not None:
            raise EstructuraCambiada(f"Error consultando endpoint JSON de BOPBA: {ultimo_error}") from ultimo_error

        resultados: list[Licitacion] = []

        for href, lista_frag in sorted(paginas_fragmentos.items()):
            unicos: list[str] = []
            for f in lista_frag:
                f_limpio = re.sub(r"\s+", " ", f).strip()
                if f_limpio and f_limpio not in unicos:
                    unicos.append(f_limpio)
            texto = " | ".join(unicos)

            if not re.search(r"Licitaci[óo]n\s+(?:P[úu]blica|Privada)", texto, re.IGNORECASE):
                continue

            if not es_de_obra_o_arquitectura(texto):
                continue

            m_ap = re.search(
                r"(?:Fecha\s*(?:y\s*hora\s*)?de\s*apertura(?:\s*de\s*(?:ofertas|sobres|propuestas))?|Apertura\s*de\s*(?:ofertas|propuestas|sobres))\s*[:\-]?\s*([^|]{6,120}?)(?:\.\s+[A-ZÁÉÍÓÚ]|\||$)",
                texto,
                re.IGNORECASE,
            )
            if not m_ap:
                continue

            ap_str = m_ap.group(1).strip(" .")
            f_dt = parsear_fecha_apertura(ap_str)
            if not f_dt or f_dt < hoy:
                continue

            m_mun = re.search(
                r"(MUNICIPALIDAD\s+DE\s+[A-ZÁÉÍÓÚÑ\s]{3,35}?|MINISTERIO\s+DE\s+[A-ZÁÉÍÓÚÑ\s]{3,40}?|HIE\s+[A-ZÁÉÍÓÚÑ.\s]{5,45}?)(?=\s+SECRETAR|\s+Licitaci|\s+POR\s+\d|\s*\|)",
                texto,
            )
            organismo = f"BOPBA - {m_mun.group(1).strip()}" if m_mun else self.nombre

            m_lic = re.search(
                r"(Licitaci[óo]n\s+(?:P[úu]blica|Privada)(?:\s+Nacional|\s+Internacional)?\s*(?:N[°ºo.]*)?\s*[\d/\-]+)",
                texto,
                re.IGNORECASE,
            )
            numero = m_lic.group(1).strip() if m_lic else href.split("/")[-1]

            m_pres_num = re.search(
                r"Presupuesto\s*oficial\s*[:\-]?[^|$]{0,80}?(\$\s*[\d.,]+)",
                texto,
                re.IGNORECASE,
            )
            if m_pres_num:
                presupuesto = m_pres_num.group(1).strip().rstrip(".")
            else:
                m_pres_txt = re.search(
                    r"Presupuesto\s*oficial\s*[:\-]?\s*([^|]{4,95}?)(?:\.\s+[A-Z]|\||$)",
                    texto,
                    re.IGNORECASE,
                )
                presupuesto = m_pres_txt.group(1).strip(" .") if m_pres_txt else NO_INFORMADO

            m_pliego = re.search(
                r"Valor\s*de(?:l)?\s*pliego\s*[:\-]?\s*([^|]{3,70}?)(?:\.\s+[A-Z]|Fecha|Apertura|Expediente|\||$)",
                texto,
                re.IGNORECASE,
            )
            valor_pliego = m_pliego.group(1).strip(" .") if m_pliego else NO_INFORMADO

            objeto_limpio = re.sub(
                r"BOLETÍN OFICIAL DE LA PROVINCIA DE BUENOS AIRES\s*La Plata\s*>\s*[a-záéíóú]+\s+\d+\s+de\s+[a-záéíóú]+\s+de\s+\d{4}",
                "",
                texto,
                flags=re.IGNORECASE,
            )
            objeto_limpio = re.sub(r"\s+", " ", objeto_limpio.replace("\u25e2", "")).strip(" |.-")

            link_completo = f"https://boletinoficial.gba.gob.ar{href}" if href.startswith("/") else href
            id_fuente = re.sub(r"[^a-zA-Z0-9_-]", "_", href.strip("/"))

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_fuente,
                    organismo=organismo,
                    numero=numero,
                    objeto=objeto_limpio[:420],
                    link=link_completo,
                    presupuesto_oficial=presupuesto,
                    apertura=ap_str,
                    valor_pliego=valor_pliego,
                )
            )

        return resultados
