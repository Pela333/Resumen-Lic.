"""Fuente: Ministerio de Hábitat y Desarrollo Urbano de la Provincia de Buenos Aires.

Monitorea licitaciones de viviendas, urbanización, espacios públicos y obras hidráulicas.
URL Oficial: https://www.gba.gob.ar/habitat/licitaciones
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_fecha(texto: str) -> datetime.date | None:
    m1 = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if m1:
        try:
            return datetime(int(m1.group(3)), int(m1.group(2)), int(m1.group(1))).date()
        except ValueError:
            pass
    m2 = re.search(r"(\d{1,2})\s+de\s+([a-zA-ZáéíóúÁÉÍÓÚ]+)\s+de\s+(\d{4})", texto, re.IGNORECASE)
    if m2:
        dia = int(m2.group(1))
        mes_nombre = m2.group(2).lower()
        anio = int(m2.group(3))
        mes = MESES.get(mes_nombre)
        if mes:
            try:
                return datetime(anio, mes, dia).date()
            except ValueError:
                pass
    return None


@registrar
class HabitatPba(Fuente):
    clave = "habitat_pba"
    nombre = "Ministerio de Hábitat y Desarrollo Urbano PBA"
    url = "https://www.gba.gob.ar/habitat/licitaciones"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(self.url, timeout=self.web.timeout)
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error al conectar con Hábitat PBA: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        region = soup.find(class_="region-content")
        if not region:
            raise EstructuraCambiada("No se encontró 'region-content' en Hábitat PBA.")

        items = region.find_all("div", class_=lambda x: x and ("views-row" in x or "node" in x))
        resultados: list[Licitacion] = []
        urls_vistas: set[str] = set()

        for it in items:
            a_tag = it.find("a", href=True)
            if not a_tag or "ver detalle" not in a_tag.get_text(strip=True).lower():
                continue

            href = a_tag["href"]
            if href in urls_vistas:
                continue
            urls_vistas.add(href)

            link_detalle = f"https://www.gba.gob.ar{href}" if href.startswith("/") else href

            title_el = it.find(["h2", "h3", "h4", "h5"])
            objeto = title_el.get_text(strip=True) if title_el else ""

            try:
                r_det = sesion.get(link_detalle, timeout=10)
                if r_det.status_code != 200:
                    continue
                s_det = BeautifulSoup(r_det.text, "html.parser")
                reg_det = s_det.find(class_="region-content") or s_det
                det_text = reg_det.get_text(separator=" ", strip=True)

                # Si ya tiene acta de apertura o adjudicación, la descartamos
                if "acta de apertura" in det_text.lower() or "adjudicaci" in det_text.lower():
                    continue

                m_ap = re.search(r"(?:apertura|fecha)[:\s]+([^.\n]{10,40})", det_text, re.IGNORECASE)
                ap_str = m_ap.group(1).strip() if m_ap else ""
                f_dt = _parse_fecha(ap_str)
                if f_dt is None or f_dt < hoy:
                    continue

                m_exp = re.search(r"expediente[:\s]+([A-Z0-9\-]+)", det_text, re.IGNORECASE)
                expediente = m_exp.group(1).strip() if m_exp else ""

                m_pres = re.search(r"presupuesto oficial[:\s]+([^.\n]{5,50})", det_text, re.IGNORECASE)
                presupuesto = m_pres.group(1).strip() if m_pres else NO_INFORMADO

                id_fuente = expediente if expediente else re.sub(r"[^a-zA-Z0-9]+", "-", href).strip("-")

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=id_fuente,
                        organismo=self.nombre,
                        numero=expediente if expediente else id_fuente,
                        objeto=objeto,
                        link=link_detalle,
                        presupuesto_oficial=presupuesto,
                        apertura=ap_str,
                    )
                )
            except Exception as exc:
                _log.debug("Error procesando detalle de Hábitat %s: %s", link_detalle, exc)

        if not urls_vistas:
            raise EstructuraCambiada("No se encontraron publicaciones de licitaciones en la página de Hábitat PBA.")

        return resultados
