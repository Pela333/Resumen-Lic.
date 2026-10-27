"""Fuente: Ministerio de Infraestructura y Servicios Públicos de la Provincia de Buenos Aires (Minfra PBA).

Portal oficial de licitaciones de obra pública provincial (viales, hidráulicas, arquitectura, acueductos).
URL Oficial: https://www.minfra.gba.gob.ar/licitacionesV2/obras
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


@registrar
class MinfraPba(Fuente):
    clave = "minfra_pba"
    nombre = "Ministerio de Infraestructura y Servicios Públicos PBA"
    url = "https://www.minfra.gba.gob.ar/licitacionesV2/obras"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(self.url, timeout=self.web.timeout)
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error al conectar con Minfra PBA: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        tabla = soup.find("table", id="myTable")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla 'myTable' en Minfra PBA.")

        tbody = tabla.find("tbody")
        filas = tbody.find_all("tr") if tbody else tabla.find_all("tr")

        resultados: list[Licitacion] = []

        for tr in filas:
            item = tr.find("li", class_="list-group-item")
            if not item:
                continue

            id_lic = (item.get("id") or "").strip()
            title_el = item.find(["h5", "h4", "h6"])
            objeto = title_el.get_text(strip=True) if title_el else ""

            datos: dict[str, str] = {}
            for p in item.find_all("p"):
                span = p.find("span")
                if span:
                    label = span.get_text(strip=True).rstrip(":")
                    val = p.get_text(strip=True)[len(label):].strip(" :")
                    datos[label] = val

            fecha_str = datos.get("Fecha de apertura", "")
            estado = datos.get("Estado", "")
            expediente = datos.get("Expediente", "")
            comitente = datos.get("Comitente", "")
            municipio = datos.get("Municipio/s", "")
            proc = datos.get("Número de procedimiento", "")

            # Descartar licitaciones finalizadas o canceladas
            if any(e in estado.lower() for e in ["adjudicad", "finalizad", "desiert", "fracasad", "cancelad"]):
                continue

            # Parsing de fecha (DD/MM/YYYY)
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", fecha_str)
            if not m:
                continue
            try:
                f_dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
            except ValueError:
                continue

            if f_dt < hoy:
                continue

            numero = proc if proc else expediente
            link_detalle = f"https://www.minfra.gba.gob.ar/licitacionesV2/bidding/show/{id_lic}/" if id_lic else self.url

            # Enriquecimiento con ficha de detalle (presupuesto oficial y lugar exacto de apertura)
            presupuesto_str = NO_INFORMADO
            lugar_aper = NO_INFORMADO
            try:
                r_det = sesion.get(link_detalle, timeout=10)
                if r_det.status_code == 200:
                    s_det = BeautifulSoup(r_det.text, "html.parser")
                    for p_det in s_det.find_all(["p", "div"]):
                        t_det = p_det.get_text(strip=True)
                        if "presupuesto oficial:" in t_det.lower():
                            val_p = t_det.split(":")[-1].strip()
                            if val_p:
                                presupuesto_str = f"$ {val_p}"
                        elif "lugar de apertura:" in t_det.lower():
                            val_l = t_det.split(":")[-1].strip()
                            if val_l:
                                lugar_aper = val_l
            except Exception as exc:
                _log.debug("No se pudo obtener la ficha de detalle de Minfra %s: %s", id_lic, exc)

            apertura_completa = fecha_str
            if lugar_aper != NO_INFORMADO:
                apertura_completa = f"{fecha_str} - {lugar_aper}"

            extra: dict[str, str] = {"Estado": estado}
            if comitente:
                extra["Comitente"] = comitente
            if municipio:
                extra["Municipio"] = municipio
            if expediente and expediente != numero:
                extra["Expediente"] = expediente

            organismo = f"Min. Infraestructura PBA - {comitente}" if comitente else self.nombre

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_lic or expediente or numero,
                    organismo=organismo,
                    numero=numero,
                    objeto=objeto,
                    link=link_detalle,
                    presupuesto_oficial=presupuesto_str,
                    apertura=apertura_completa,
                    extra=extra,
                )
            )

        return resultados
