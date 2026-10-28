"""Fuente: Boletín Oficial de la República Argentina (BORA) - Tercera Sección (Contrataciones).

Monitorea la publicación legal diaria obligatoria de llamados a licitación pública, privada,
subastas y contrataciones de obras civiles, viales e infraestructura de todos los organismos nacionales.
URL Oficial: https://www.boletinoficial.gob.ar/seccion/tercera
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class BoletinOficialNacion(Fuente):
    clave = "boletin_oficial_nacion"
    nombre = "Boletín Oficial de la Nación - 3ª Sección"
    url = "https://www.boletinoficial.gob.ar/seccion/tercera"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion_rapida = requests.Session()
        sesion_rapida.headers.update({"User-Agent": "Mozilla/5.0"})

        try:
            resp = sesion_rapida.get(
                self.url,
                timeout=12,
                verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con Boletín Oficial de la Nación: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        links_avisos = [
            a for a in soup.find_all("a", href=True)
            if "/detalleAviso/tercera/" in a["href"]
        ]

        if not links_avisos:
            raise EstructuraCambiada("No se encontraron avisos en la Tercera Sección del Boletín Oficial.")

        resultados: list[Licitacion] = []
        vistos: set[str] = set()
        t_inicio = time.monotonic()

        for a in links_avisos:
            if time.monotonic() - t_inicio > 22:
                _log.debug("Presupuesto de tiempo alcanzado en BORA 3ª Sección; continuando.")
                break

            href = a["href"]
            if href in vistos:
                continue
            vistos.add(href)

            texto_resumen = a.get_text(" | ", strip=True)
            if any(
                x in texto_resumen.lower()
                for x in ("adjudicaci", "preadjudicaci", "desiert", "fracasad", "deja sin efecto")
            ):
                continue

            partes = [p.strip() for p in texto_resumen.split("|") if p.strip()]
            organismo_tit = partes[0] if partes else self.nombre
            proceso_tit = partes[1] if len(partes) > 1 else ""

            link_aviso = f"https://www.boletinoficial.gob.ar{href}" if href.startswith("/") else href

            try:
                r_det = sesion_rapida.get(link_aviso, timeout=(4, 5), verify=False)
                if r_det.status_code != 200:
                    continue
                s_det = BeautifulSoup(r_det.text, "html.parser")
                cuerpo = s_det.find(id="cuerpoDetalleAviso") or s_det.find(class_="cuerpoDetalleAviso")
                if not cuerpo:
                    continue
                t_det = cuerpo.get_text(" \n ", strip=True)

                m_obj = re.search(
                    r"Objeto:\s*(.*?)(?:Retiro|Lugar|Consulta|Plazo|\n\n|$)",
                    t_det,
                    re.DOTALL | re.IGNORECASE,
                )
                objeto = re.sub(r"\s+", " ", m_obj.group(1)).strip() if m_obj else proceso_tit

                if not es_de_obra_o_arquitectura(objeto):
                    continue

                m_ap = re.search(
                    r"Acto de apertura.*?Plazo y horario:\s*(.*?)(?:Lugar|\n\n|$)",
                    t_det,
                    re.DOTALL | re.IGNORECASE,
                )
                ap_str = re.sub(r"\s+", " ", m_ap.group(1)).strip() if m_ap else ""

                if not ap_str:
                    m_f_gen = re.search(r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{2}:\d{2})", t_det)
                    ap_str = m_f_gen.group(1) if m_f_gen else ""

                if ap_str:
                    f_dt = parsear_fecha_apertura(ap_str)
                    if f_dt and f_dt < hoy:
                        continue

                m_exp = re.search(r"Expediente N°:\s*([A-Z0-9\-#]+)", t_det, re.IGNORECASE)
                expediente = m_exp.group(1).strip() if m_exp else ""

                m_pres = re.search(r"Presupuesto Oficial[:\s]+(\$[\d.,]+)", t_det, re.IGNORECASE)
                presupuesto = m_pres.group(1).strip() if m_pres else NO_INFORMADO

                m_id = re.search(r"/tercera/(\d+)/", href)
                id_aviso = m_id.group(1) if m_id else href

                numero = proceso_tit if proceso_tit else (expediente if expediente else id_aviso)

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=id_aviso,
                        organismo=f"BORA - {organismo_tit}",
                        numero=numero,
                        objeto=objeto,
                        link=link_aviso,
                        presupuesto_oficial=presupuesto,
                        apertura=ap_str if ap_str else "Ver pliego en BORA",
                    )
                )
            except Exception as exc:
                _log.debug("Error procesando aviso BORA %s: %s", href, exc)

        return resultados
