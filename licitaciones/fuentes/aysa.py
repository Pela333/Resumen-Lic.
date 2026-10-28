"""Fuente: AySA - Agua y Saneamientos Argentinos S.A.

Empresa pública concesionaria de los servicios de agua potable y saneamiento en el AMBA.
Monitorea obras de expansión de redes, estaciones de bombeo, plantas potabilizadoras y de tratamiento.
URL Oficial: https://www.aysa.com.ar/proveedores/licitaciones/Licitaciones-Bienes-Servicios/
API JSON Oficial: https://www.aysa.com.ar/api/licitaciones/getLicitacionesObraByFiltersPublic
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class Aysa(Fuente):
    clave = "aysa"
    nombre = "AySA - Agua y Saneamientos Argentinos"
    url = "https://www.aysa.com.ar/proveedores/licitaciones/Licitaciones-Bienes-Servicios/"
    api_url = "https://www.aysa.com.ar/api/licitaciones/getLicitacionesObraByFiltersPublic"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.post(
                self.api_url,
                json={"current": 1, "rowCount": 50},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con API de AySA: {exc}") from exc

        filas: list[dict[str, Any]] = data.get("rows", [])
        if not filas and data.get("total", 0) == 0:
            raise EstructuraCambiada("La API de AySA devolvió 0 registros totales.")

        resultados: list[Licitacion] = []

        for row in filas:
            ap_str = row.get("AperturaOfertas") or row.get("PresentacionOfertas")
            if not ap_str:
                continue

            try:
                ap_dt = datetime.fromisoformat(ap_str.replace("Z", "")).date()
            except ValueError:
                continue

            if ap_dt < hoy:
                continue

            objeto = (row.get("Objeto") or "").strip()
            if not es_de_obra_o_arquitectura(objeto):
                continue

            lic_id = str(row.get("Id") or "")
            numero = str(row.get("NroLicitacion") or lic_id)
            estado = str(row.get("EstadoNombre") or "")
            moneda = str(row.get("TipoMoneda") or "")
            pres = row.get("Presupuesto")
            presupuesto_str = f"{moneda} {pres}".strip() if pres else NO_INFORMADO

            link = f"https://www.aysa.com.ar/portal/proveedores/licitaciones/Licitaciones-Bienes-Servicios/Detalle_Licitaciones_Bienes?id={lic_id}" if lic_id else self.url

            extra = {}
            if estado:
                extra["Estado"] = estado
            if row.get("LocalidadNombre"):
                extra["Localidad"] = str(row["LocalidadNombre"])

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto,
                    link=link,
                    presupuesto_oficial=presupuesto_str,
                    apertura=ap_str,
                    extra=extra,
                )
            )

        return resultados
