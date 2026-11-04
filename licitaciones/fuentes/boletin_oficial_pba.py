"""Fuente: Boletín Oficial de la Provincia de Buenos Aires (BOPBA) - Sección Oficial y 135 Municipios.

Descarga y procesa directamente el PDF oficial diario de la Sección Oficial
(donde se publican todas las licitaciones provinciales y de los 135 municipios bonaerenses),
localizando mediante el sumario el rango exacto de páginas de 'LICITACIONES'
para indexar cada llamado individual con su comitente, presupuesto, fecha de apertura y enlace a la página exacta.
URL Oficial: https://boletinoficial.gba.gob.ar/
"""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import urllib3
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..filtro import es_de_obra_o_arquitectura
from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class BoletinOficialPba(Fuente):
    clave = "boletin_oficial_pba"
    nombre = "Boletín Oficial PBA (Oficial y 135 Municipios)"
    url = "https://boletinoficial.gba.gob.ar/"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = requests.Session()
        sesion.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        # 1. Obtener lista de ediciones recientes desde /ediciones-anteriores y la portada
        ediciones: list[dict] = []
        try:
            r_ant = sesion.get("https://boletinoficial.gba.gob.ar/ediciones-anteriores", verify=False, timeout=15)
            if r_ant.status_code == 200:
                soup = BeautifulSoup(r_ant.text, "html.parser")
                for p in soup.find_all("div", class_="panel panel-default"):
                    heading = p.find(class_="panel-heading")
                    if not heading:
                        continue
                    txt = heading.get_text(" ", strip=True)
                    m = re.search(r"BOLET[IÍ]N\s+N[°ºo]?\s*(\d+)\s*-\s*(\d{2}/\d{2}/\d{4})", txt, re.IGNORECASE)
                    if not m:
                        continue
                    num_bol = m.group(1)
                    f_dt = datetime.strptime(m.group(2), "%d/%m/%Y").date()

                    body = p.find(class_="panel-body")
                    if not body:
                        continue
                    link_oficial = None
                    for sec in body.find_all(class_="section"):
                        stitle = sec.find(class_="body-title")
                        if stitle and "OFICIAL" in stitle.get_text().upper():
                            a_ver = sec.find("a", href=lambda h: h and "ver" in h)
                            if a_ver:
                                link_oficial = a_ver.get("href")
                                break
                    if link_oficial:
                        full_link = (
                            f"https://boletinoficial.gba.gob.ar{link_oficial}"
                            if link_oficial.startswith("/")
                            else link_oficial
                        )
                        ediciones.append({
                            "numero": num_bol,
                            "fecha": f_dt,
                            "url": full_link,
                        })
        except Exception as exc:
            _log.warning("No se pudo consultar /ediciones-anteriores: %s", exc)

        # Si no hubo ediciones en anteriores, probar portada
        if not ediciones:
            try:
                r_home = sesion.get("https://boletinoficial.gba.gob.ar/", verify=False, timeout=15)
                soup = BeautifulSoup(r_home.text, "html.parser")
                for a in soup.find_all("a", href=lambda h: h and "/secciones/" in h and "/ver" in h):
                    if "OFICIAL" in a.get_text().upper():
                        href = a.get("href")
                        full_link = f"https://boletinoficial.gba.gob.ar{href}" if href.startswith("/") else href
                        ediciones.append({
                            "numero": "Actual",
                            "fecha": hoy,
                            "url": full_link,
                        })
                        break
            except Exception as exc:
                _log.warning("No se pudo consultar portada de BOPBA: %s", exc)

        if not ediciones:
            raise EstructuraCambiada("No se encontraron enlaces a la Sección Oficial del Boletín Oficial PBA")

        # Filtrar hasta 3 ediciones recientes (no mayores a 5 días)
        limite_fecha = hoy - timedelta(days=5)
        ediciones_filtradas = [e for e in ediciones if e["fecha"] >= limite_fecha][:3]
        if not ediciones_filtradas:
            ediciones_filtradas = ediciones[:1]

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for ed in ediciones_filtradas:
            url_pdf = ed["url"]
            try:
                resp = sesion.get(url_pdf, verify=False, timeout=30)
                if resp.status_code != 200 or len(resp.content) < 5000:
                    continue
                reader = PdfReader(io.BytesIO(resp.content))
            except Exception as exc:
                _log.warning("Error descargando PDF %s: %s", url_pdf, exc)
                continue

            # 2. Localizar páginas de la sección LICITACIONES a través del sumario
            sumario_text = ""
            for pno in range(min(5, len(reader.pages))):
                ptxt = reader.pages[pno].extract_text()
                if "sumario" in ptxt.lower():
                    sumario_text = ptxt
                    break

            start_page = 1
            end_page = len(reader.pages)
            if sumario_text:
                m_lic = re.search(r"LICITACIONES\s*\n\s*(\d+)", sumario_text, re.IGNORECASE)
                if m_lic:
                    start_page = int(m_lic.group(1))
                    sections = re.findall(r"([A-ZÁÉÍÓÚÑ\s]{4,35})\s*\n\s*(\d+)", sumario_text)
                    found_lic = False
                    for sec_name, pnum in sections:
                        if "LICITACION" in sec_name.upper():
                            found_lic = True
                            continue
                        if found_lic:
                            end_page = int(pnum)
                            break

            # 3. Extraer texto del rango de páginas
            pages_content: list[tuple[int, str]] = []
            for pno in range(start_page - 1, min(end_page + 1, len(reader.pages))):
                ptxt = reader.pages[pno].extract_text()
                for stop_sec in ("COLEGIACIONES", "TRANSFERENCIAS", "CONVOCATORIAS", "SOCIEDADES"):
                    if stop_sec in ptxt:
                        ptxt = ptxt[: ptxt.find(stop_sec)]
                ptxt = re.sub(
                    r"BOLET[IÍ]N OFICIAL DE LA PROVINCIA DE BUENOS AIRES\s+La Plata\s*>\s*[^\n]+\s+SECCI[OÓ]N OFICIAL\s*>\s*p[aá]gina\s*\d+",
                    "",
                    ptxt,
                    flags=re.IGNORECASE,
                )
                ptxt = ptxt.replace("\u25e2", "")
                pages_content.append((pno + 1, ptxt))

            combined_text = ""
            page_offsets: list[tuple[int, int]] = []
            for pnum, ptxt in pages_content:
                offset = len(combined_text)
                page_offsets.append((offset, pnum))
                combined_text += ptxt + "\n"

            def _obtener_pagina(pos: int) -> int:
                actual = start_page
                for off, pn in page_offsets:
                    if pos >= off:
                        actual = pn
                    else:
                        break
                return actual

            # 4. Encontrar llamados a licitación
            patron_lic = re.compile(
                r"(^[ \t]*(?:Licitaci[óo]n\s+(?:P[úu]blica|Privada|Internacional|Nacional|Abreviada)|LPI\b|Proceso\s+de\s+Compra|Proceso\s+PBAC|Proceso\s+N[°ºo])[^\n]*)",
                re.MULTILINE | re.IGNORECASE,
            )
            matches = list(patron_lic.finditer(combined_text))
            if not matches:
                continue

            tenders_data = []
            ultimo_organismo = "Provincia de Buenos Aires"

            for i, m in enumerate(matches):
                lic_titulo = m.group(1).strip()
                pos_lic = m.start()
                pos_lic_end = m.end()
                num_pagina = _obtener_pagina(pos_lic)

                prev_end = matches[i - 1].end() if i > 0 else 0
                between_text = combined_text[prev_end:pos_lic].strip()

                lines = [l.strip() for l in between_text.split("\n") if l.strip()]

                idx_org = len(lines)
                for idx in range(len(lines) - 1, -1, -1):
                    l = lines[idx]
                    if re.match(
                        r"^(?:[a-z]{3}\.?\s+\d+\s+v\.\s+[a-z]{3}\.?\s+\d+|DISPO|RESO|EX-|Decreto|Expediente|Expte|Nota)\b",
                        l,
                        re.IGNORECASE,
                    ):
                        break
                    if re.match(
                        r"^(?:MUNICIPALIDAD|MINISTERIO|SECRETAR[IÍ]A|DIRECCI[OÓ]N|PROCURACI[OÓ]N|SUPREMA|CAJA|AUTOPISTAS|AUTORIDAD|INSTITUTO|BANCO|HOSPITAL|HIGA|HIA|HZA|HMA|DEFENSOR[IÍ]A)\b",
                        l,
                        re.IGNORECASE,
                    ):
                        idx_org = idx
                        continue
                    if l.isupper() and 4 <= len(l) <= 35 and not any(
                        k in l for k in ["PÁGINA", "SECCIÓN", "BOLETÍN", "PLATA", "PROVINCIA", "DÍAS"]
                    ):
                        idx_org = idx
                        continue
                    break

                org_lines = [l for l in lines[idx_org:] if l.upper() != "LICITACIONES"]
                if org_lines:
                    organismo = " - ".join(org_lines)
                    ultimo_organismo = organismo
                else:
                    organismo = ultimo_organismo

                tenders_data.append({
                    "organismo": organismo,
                    "lic_titulo": lic_titulo,
                    "pos_lic": pos_lic,
                    "pos_lic_end": pos_lic_end,
                    "num_pagina": num_pagina,
                })

            for i, t in enumerate(tenders_data):
                next_m_start = matches[i + 1].start() if i + 1 < len(matches) else len(combined_text)
                raw_following = combined_text[t["pos_lic_end"] : next_m_start]
                if i + 1 < len(tenders_data):
                    next_first_org_line = tenders_data[i + 1]["organismo"].split(" - ")[0]
                    if "\n" + next_first_org_line in raw_following:
                        t["cuerpo"] = raw_following.split("\n" + next_first_org_line)[0].strip()
                    else:
                        t["cuerpo"] = raw_following.strip()
                else:
                    t["cuerpo"] = raw_following.strip()

            # 5. Filtrar y construir objetos Licitacion
            for t in tenders_data:
                org = t["organismo"]
                lic_titulo = t["lic_titulo"]
                cuerpo = t["cuerpo"]
                num_pag = t["num_pagina"]

                # Exclusión explícita de salud (solicitada expresamente por el usuario)
                if re.search(r"\b(?:ministerio\s+de\s+salud|hospital\b|higa\b|hiea\b|hza\b|hma\b)", org, re.IGNORECASE):
                    continue

                texto_evaluar = f"{org}\n{lic_titulo}\n{cuerpo}"

                if not es_de_obra_o_arquitectura(texto_evaluar, organismo=org):
                    continue

                # Presupuesto oficial
                m_pres = re.search(
                    r"Presupuesto\s*(?:oficial|del\s+servicio|estimado)?.*?(?:\$|USD)\s*([\d.,]+)",
                    cuerpo,
                    re.IGNORECASE | re.DOTALL,
                )
                presupuesto = f"${m_pres.group(1).rstrip('.')}" if m_pres else NO_INFORMADO

                # Apertura
                m_ap = re.search(
                    r"(?:apertura\s+de\s+(?:las\s+)?(?:propuestas|ofertas|sobres)\s+se\s+realizar[aá][^.\n]*?el\s+d[ií]a|"
                    r"acto\s+de\s+apertura[^.\n]*?el\s+d[ií]a|"
                    r"apertura\s+de\s+(?:las\s+)?ofertas\s+es\s+el|"
                    r"Fecha\s*(?:y\s*hora\s*)?de\s*apertura(?:\s*de\s*(?:ofertas|propuestas|sobres))?|"
                    r"Apertura(?:\s*de\s*(?:ofertas|propuestas|sobres))?)\s*[:\-]?\s*([^\n.]{5,60}?)(?:,\s*siendo|\.|\n|$)",
                    cuerpo,
                    re.IGNORECASE,
                )
                apertura_str = m_ap.group(1).strip(" .") if m_ap else NO_INFORMADO
                if apertura_str != NO_INFORMADO:
                    f_dt = parsear_fecha_apertura(apertura_str)
                    if f_dt and f_dt < hoy:
                        continue

                # Pliego
                m_pliego = re.search(
                    r"Valor\s*de(?:l)?\s*pliego\s*[:\-]?\s*([^|\n]{3,60}?)(?:\.\s+[A-Z]|Presupuesto|Fecha|Apertura|Expediente|\||$)",
                    cuerpo,
                    re.IGNORECASE,
                )
                valor_pliego = m_pliego.group(1).strip(" .") if m_pliego else NO_INFORMADO

                # Objeto / Motivo
                m_obj = re.search(
                    r"(?:Denominaci[óo]n|Motivo|Objeto|cuyo\s+objeto\s+es\s+la\s+obra\s+denominada|para\s+(?:la\s+)?(?:Ejecuci[óo]n|Contratar\s+la\s+Ejecuci[óo]n|licitar\s+la\s+Obra)|\bObra\b)\s*[:\-]?\s*([^\n]+(?:\n[^\n]+)?)",
                    cuerpo,
                    re.IGNORECASE,
                )
                if m_obj:
                    objeto_limpio = re.sub(r"\s+", " ", m_obj.group(1)).strip(" |.-")
                else:
                    primeras_lineas = [l.strip() for l in cuerpo.split("\n") if l.strip()]
                    objeto_limpio = re.sub(r"\s+", " ", " ".join(primeras_lineas[:2])).strip(" |.-")

                # Limpieza de prefijos y colas redundantes en el objeto
                objeto_limpio = re.sub(r"^(?:de\s+la\s+obra\b|obra\b)\s*[:\-]?\s*", "", objeto_limpio, flags=re.IGNORECASE)
                objeto_limpio = re.sub(r"[,;]?\s*cuyo\s+presupuesto\s+oficial.*$", "", objeto_limpio, flags=re.IGNORECASE)
                objeto_limpio = re.sub(r"\s+", " ", objeto_limpio).strip(" |.-")

                link_pagina = f"{url_pdf}#page={num_pag}"
                id_fuente = f"bopba_{ed['numero']}_{num_pag}_{re.sub(r'[^a-zA-Z0-9]', '_', lic_titulo)}"

                if id_fuente in vistos:
                    continue
                vistos.add(id_fuente)

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=id_fuente,
                        organismo=f"BOPBA - {org}",
                        numero=lic_titulo,
                        objeto=objeto_limpio[:420],
                        link=link_pagina,
                        presupuesto_oficial=presupuesto,
                        apertura=apertura_str,
                        valor_pliego=valor_pliego,
                    )
                )

        return resultados
