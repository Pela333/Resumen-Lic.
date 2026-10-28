"""Fuente: Ambiente Nación - Licitaciones Especiales con Financiamiento Internacional.

Monitorea licitaciones y solicitudes de cotización de la Subsecretaría de Ambiente de la Nación
financiadas por organismos internacionales (BID, Banco Mundial, PNUD).
URL Oficial: https://www.argentina.gob.ar/ambiente/licitaciones-especiales
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


@registrar
class AmbienteNacion(Fuente):
    clave = "ambiente_nacion"
    nombre = "Ambiente Nación - Licitaciones Especiales"
    url = "https://www.argentina.gob.ar/ambiente/licitaciones-especiales"

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
            raise EstructuraCambiada(f"Error conectando con Ambiente Nación: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=lambda h: h and "/ambiente/licitaciones-especiales/" in h)

        if not links:
            raise EstructuraCambiada("No se encontraron publicaciones en Ambiente Nación.")

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for a in links:
            href = a["href"]
            if href in vistos:
                continue
            vistos.add(href)

            texto = a.get_text(" ", strip=True)
            link = f"https://www.argentina.gob.ar{href}" if href.startswith("/") else href

            m_fecha = re.search(r"(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})", texto)
            if m_fecha:
                dia = int(m_fecha.group(1))
                mes_str = m_fecha.group(2).lower()
                anio = int(m_fecha.group(3))
                mes = MESES.get(mes_str)
                if mes:
                    try:
                        f_dt = datetime(anio, mes, dia).date()
                        if f_dt < hoy:
                            continue
                    except ValueError:
                        pass

            m_num = re.search(r"(?:solicitud|licitaci[oó]n)[^0-9]*([0-9\-/]+)", texto, re.IGNORECASE)
            numero = m_num.group(0).strip() if m_num else texto[:30]

            objeto = re.sub(r"^\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4}", "", texto).strip()

            if not es_de_obra_o_arquitectura(objeto):
                continue

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto,
                    link=link,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura=NO_INFORMADO,
                )
            )

        return resultados
