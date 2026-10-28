"""Fuente: Ministerio de Ambiente PBA - Licitaciones Proyecto PNUD.

Monitorea licitaciones públicas e internacionales de parques ambientales,
saneamiento, gestión de residuos y puesta en valor de espacios públicos en PBA.
URL Oficial: https://www.ambiente.gba.gob.ar/contenido/licitaciones_proyecto_pnud_arg22008_0
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


def _parsear_fecha_es(texto: str) -> datetime.date | None:
    m = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-zA-ZáéíóúÁÉÍÓÚ]+)[,\s]+(?:de\s+)?(\d{4})", texto, re.IGNORECASE)
    if m:
        dia = int(m.group(1))
        mes = MESES.get(m.group(2).lower())
        anio = int(m.group(3))
        if mes:
            try:
                return datetime(anio, mes, dia).date()
            except ValueError:
                pass
    m2 = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if m2:
        try:
            return datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1))).date()
        except ValueError:
            pass
    return None


@registrar
class AmbientePba(Fuente):
    clave = "ambiente_pba"
    nombre = "Ministerio de Ambiente PBA (PNUD)"
    url = "https://www.ambiente.gba.gob.ar/contenido/licitaciones_proyecto_pnud_arg22008_0"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con Ambiente PBA: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        texto = soup.get_text(" ", strip=True)
        if "licitaciones proyecto pnud" not in texto.lower():
            raise EstructuraCambiada("No se encontró la sección de licitaciones en Ambiente PBA.")

        bloques = re.split(r"(?=Licitaci[oó]n\s+(?:P[uú]blica|Privada))", texto, flags=re.IGNORECASE)
        resultados: list[Licitacion] = []

        for b in bloques:
            if not re.match(r"^Licitaci[oó]n\s+(?:P[uú]blica|Privada)", b.strip(), re.IGNORECASE):
                continue

            m_tit = re.search(r"^(Licitaci[oó]n[^\n|]+?)(?:Plazo de Presentaci|Fecha de Apertura|$)", b.strip(), re.IGNORECASE)
            titulo = m_tit.group(1).strip() if m_tit else b[:100].strip()

            m_ap = re.search(r"Fecha de Apertura de Ofertas:\s*([^.]+)", b, re.IGNORECASE)
            ap_str = m_ap.group(1).strip() if m_ap else ""

            f_dt = _parsear_fecha_es(ap_str)
            if f_dt is None or f_dt < hoy:
                continue

            m_num = re.search(r"N[°º]\s*([0-9/\-]+)", titulo, re.IGNORECASE)
            numero = f"Licitación N° {m_num.group(1)}" if m_num else titulo[:30]

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=titulo,
                    link=self.url,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura=ap_str,
                )
            )

        return resultados
