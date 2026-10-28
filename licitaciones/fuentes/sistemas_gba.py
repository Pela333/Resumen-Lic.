"""Fuente: Sistemas GBA - Consulta Consolidada de Contrataciones de la Provincia de Buenos Aires.

Consulta el formulario PHP interno del portal de contrataciones provinciales (estado_vigencia=S)
para capturar llamados vigentes de Consejos Escolares, Vialidad y Ministerios provinciales.
URL Oficial: https://sistemas.gba.gob.ar/consulta/contrataciones/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

URL_POST = "https://sistemas.gba.gob.ar/consulta/contrataciones/contrataciones.php?mrio_id="


@registrar
class SistemasGba(Fuente):
    clave = "sistemas_gba"
    nombre = "Sistemas GBA - Contrataciones Provinciales"
    url = "https://sistemas.gba.gob.ar/consulta/contrataciones/"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.post(
                URL_POST,
                data={"accion": "requerir", "estado_vigencia": "S"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error consultando Sistemas GBA ({URL_POST}): {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        filas = soup.select("tr.ParesLink, tr.ImparesLink")
        if not filas and "Compras y Contrataciones" not in resp.text:
            raise EstructuraCambiada("El formulario de Sistemas GBA no devolvió la tabla esperada.")

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for tr in filas:
            tds = [td.get_text(" ", strip=True).replace("\xa0", " ") for td in tr.find_all("td")]
            if len(tds) < 12:
                continue

            organismo = tds[0].strip()
            exp_partes = [t.strip() for t in tds[1:6] if t.strip()]
            expediente = "-".join(exp_partes)
            nro_proc = tds[6].strip()
            anio_proc = tds[7].strip()
            tipo_proc = tds[8].strip()
            objeto = re.sub(r"\s+", " ", tds[9]).strip()
            recepcion = tds[10].strip()
            apertura = tds[11].strip()

            f_dt = parsear_fecha_apertura(apertura)
            if not f_dt or f_dt < hoy:
                continue

            es_org_obra = any(
                k in organismo.lower()
                for k in ("vialidad", "infraestructura", "obra", "arquitectura", "hidráulica", "hidraulica", "vivienda")
            )
            if not es_org_obra and not es_de_obra_o_arquitectura(objeto):
                continue

            numero = f"{tipo_proc} {nro_proc}/{anio_proc} (Exp. {expediente})"
            id_fuente = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{organismo}_{nro_proc}_{anio_proc}_{expediente}")[:90]
            if id_fuente in vistos:
                continue
            vistos.add(id_fuente)

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_fuente,
                    organismo=f"GBA - {organismo}",
                    numero=numero,
                    objeto=objeto,
                    link=self.url,
                    presupuesto_oficial=NO_INFORMADO,
                    recepcion_ofertas=recepcion if recepcion else NO_INFORMADO,
                    apertura=apertura,
                )
            )

        return resultados
