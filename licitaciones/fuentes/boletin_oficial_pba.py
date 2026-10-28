"""Fuente: Boletín Oficial de la Provincia de Buenos Aires (BOPBA) - Sección Oficial y 135 Municipios.

Utiliza el motor de búsqueda indexado de boletinoficial.gba.gob.ar (/buscar y su endpoint
JSON /boletin/YYYY-MM-DD/paginas/OFICIAL) combinando los fragmentos de 'licitacion',
'apertura' y 'presupuesto' por página (#page=N) para reconstruir avisos municipales y
provinciales de obras sin descargar el archivo PDF diario de 75 MB.
URL Oficial: https://boletinoficial.gba.gob.ar/
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

URL_BUSCAR = "https://boletinoficial.gba.gob.ar/buscar"


@registrar
class BoletinOficialPba(Fuente):
    clave = "boletin_oficial_pba"
    nombre = "Boletín Oficial PBA (Oficial y 135 Municipios)"
    url = "https://boletinoficial.gba.gob.ar/"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        desde = hoy - timedelta(days=5)
        sesion = self.web.sesion

        paginas_fragmentos: dict[str, list[str]] = defaultdict(list)

        import requests
        sesion_rapida = requests.Session()
        for palabra in ("licitacion", "apertura"):
            try:
                resp = sesion_rapida.get(
                    URL_BUSCAR,
                    params={
                        "search[date_gteq]": desde.strftime("%d/%m/%Y"),
                        "search[date_lteq]": hoy.strftime("%d/%m/%Y"),
                        "search[section]": "OFICIAL",
                        "search[words]": palabra,
                        "search[order]": "recent",
                    },
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=(6, 18),
                    verify=False,
                )
                resp.raise_for_status()
            except Exception as exc:
                if palabra == "licitacion":
                    raise EstructuraCambiada(f"Error consultando buscador de BOPBA: {exc}") from exc
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for box in soup.select(".result-box")[:3]:
                for a, exc_p in zip(box.find_all("a", class_="page"), box.find_all("p", class_="excerpt")):
                    href = a.get("href", "").strip()
                    if href:
                        paginas_fragmentos[href].append(exc_p.get_text(" ", strip=True))

                pag = box.select_one(".ajax-paginator")
                if not pag or not pag.get("data-link"):
                    continue
                link_ajax = pag["data-link"]
                total = int(pag.get("data-total", "2"))
                max_pnum = min(6, (total + 1) // 2 + 1)
                for pnum in range(2, max_pnum + 1):
                    try:
                        rj = sesion_rapida.get(
                            f"https://boletinoficial.gba.gob.ar{link_ajax}",
                            params={"pageNumber": pnum},
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=(4, 5),
                            verify=False,
                        ).json()
                        sp = BeautifulSoup("".join(rj.get("html", [])), "html.parser")
                        for a, exc_p in zip(sp.find_all("a", class_="page"), sp.find_all("p", class_="excerpt")):
                            href = a.get("href", "").strip()
                            if href:
                                paginas_fragmentos[href].append(exc_p.get_text(" ", strip=True))
                    except Exception:
                        break

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
