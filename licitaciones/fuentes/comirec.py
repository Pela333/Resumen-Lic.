"""Fuente: COMIREC - Comité de Cuenca del Río Reconquista (PBA).

Monitorea licitaciones de saneamiento, caminos de ribera, reservas urbanas
e infraestructura hidráulica en la cuenca del Río Reconquista.
URL Oficial: https://www.gba.gob.ar/comirec/contrataciones_comirec
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
class Comirec(Fuente):
    clave = "comirec"
    nombre = "COMIREC - Cuenca del Río Reconquista PBA"
    url = "https://www.gba.gob.ar/comirec/contrataciones_comirec"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(self.url, timeout=self.web.timeout)
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error al conectar con COMIREC: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        reg = soup.find(class_="region-content")
        if not reg:
            raise EstructuraCambiada("No se encontró 'region-content' en COMIREC.")

        # COMIREC organiza sus licitaciones en bloques de texto separados
        texto_completo = reg.get_text(separator="\n", strip=True)
        bloques = re.split(r"-{10,}|_{10,}", texto_completo)

        resultados: list[Licitacion] = []

        for bloque in bloques:
            if "OBJETO:" not in bloque and "Objeto:" not in bloque:
                continue

            # Descartar adjudicadas
            if "adjudicad" in bloque.lower() or "finalizad" in bloque.lower():
                continue

            m_obj = re.search(r"objeto[:\s]+(.*?)(?:Número|\.Número|Tipo|Estado|Comitente|\n\n|$)", bloque, re.IGNORECASE | re.DOTALL)
            objeto = re.sub(r"\s+", " ", m_obj.group(1)).strip() if m_obj else ""

            m_exp = re.search(r"expediente[:\s]+([A-Z0-9\-]+)", bloque, re.IGNORECASE)
            expediente = m_exp.group(1).strip() if m_exp else ""

            m_ap = re.search(r"fecha de apertura[:\s]+(.*?)(?:Lugar|Presupuesto|\n|$)", bloque, re.IGNORECASE)
            fecha_str = m_ap.group(1).strip() if m_ap else ""

            f_dt = _parse_fecha(fecha_str)
            if f_dt is None or f_dt < hoy:
                continue

            m_pres = re.search(r"presupuesto oficial[:\s]+(\$[\d.,]+)", bloque, re.IGNORECASE)
            presupuesto = m_pres.group(1).strip() if m_pres else NO_INFORMADO

            m_pbac = re.search(r"procedimiento pbac[:\s]+([A-Z0-9\-]+)", bloque, re.IGNORECASE)
            pbac_proc = m_pbac.group(1).strip() if m_pbac else ""

            numero = pbac_proc if pbac_proc else (expediente if expediente else objeto[:30])
            id_fuente = expediente if expediente else numero

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_fuente,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto,
                    link=self.url,
                    presupuesto_oficial=presupuesto,
                    apertura=fecha_str,
                )
            )

        return resultados
