"""Fuente: Corredores Viales S.A.

Empresa estatal nacional concesionaria de autopistas y corredores viales.
Monitorea obras viales, bacheo, repavimentación, corte de pasto e infraestructura de peajes.
URL Oficial: https://corredoresvialessa.com.ar/licitaciones/bienes/publicas
API JSON Oficial: https://corredoresvialessa.com.ar/api/v1/licitaciones
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")


@registrar
class CorredoresViales(Fuente):
    clave = "corredores_viales"
    nombre = "Corredores Viales S.A."
    url = "https://corredoresvialessa.com.ar/licitaciones/bienes/publicas"
    api_url = "https://corredoresvialessa.com.ar/api/v1/licitaciones"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                self.api_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con API de Corredores Viales: {exc}") from exc

        items: list[dict[str, Any]] = data.get("aaData", [])
        if not items:
            raise EstructuraCambiada("La API de Corredores Viales devolvió una lista vacía de registros.")

        resultados: list[Licitacion] = []

        for it in items:
            f_str = it.get("fecha_acto_de_apertura")
            if not f_str:
                continue

            try:
                f_dt = datetime.fromisoformat(f_str).date()
            except ValueError:
                continue

            if f_dt < hoy:
                continue

            lic_id = str(it.get("id") or "")
            numero = str(it.get("numero") or lic_id)
            tipo_nombre = str(it.get("tipo_nombre") or "Licitación")
            requerimiento = str(it.get("requerimiento") or "").strip()
            link = f"https://corredoresvialessa.com.ar/licitaciones/{lic_id}" if lic_id else self.url

            f_pres = it.get("fecha_presentacion_de_ofertas") or NO_INFORMADO

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=lic_id or numero,
                    organismo=self.nombre,
                    numero=f"{tipo_nombre} N° {numero}",
                    objeto=requerimiento,
                    link=link,
                    presupuesto_oficial=NO_INFORMADO,
                    recepcion_ofertas=str(f_pres),
                    apertura=str(f_str),
                    extra={"Tipo de Proceso": tipo_nombre},
                )
            )

        return resultados
