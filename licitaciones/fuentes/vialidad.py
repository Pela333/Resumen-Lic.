"""Fuente: Dirección de Vialidad de la Provincia de Buenos Aires (DVBA).

Consume directamente la API REST interna descubierta a partir de la SPA Angular:
- Endpoint: http://www.vialidad.gba.gov.ar/apps/Licitaciones/api/Licitaciones/getAllPublicadas
- Devuelve datos 100% estructurados en JSON en ~0.2s.
- Filtra borradores (numLic=0 o anio=0) y toma las licitaciones en estado 'Licitandose'
  o con fecha de apertura vigente.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

log = logging.getLogger("licitaciones.vialidad")


@registrar
class VialidadPba(Fuente):
    clave = "vialidad_pba"
    nombre = "Dirección de Vialidad de la Provincia de Buenos Aires"
    url = "http://www.vialidad.gba.gov.ar/apps/angular/licitaciones/#/"
    api_url = "http://www.vialidad.gba.gov.ar/apps/Licitaciones/api/Licitaciones/getAllPublicadas"

    def recolectar(self) -> list[Licitacion]:
        try:
            resp = self.web.sesion.get(
                self.api_url,
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            resp.raise_for_status()
            datos = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error al consultar la API de Vialidad PBA: {exc}") from exc

        if not isinstance(datos, list):
            raise EstructuraCambiada("La API de Vialidad no devolvió una lista JSON.")

        hoy = datetime.now().strftime("%Y-%m-%d")
        resultados: list[Licitacion] = []

        for d in datos:
            # Descartar registros vacíos o borradores
            anio = d.get("anio") or 0
            num_lic = d.get("numLic") or 0
            desc = (d.get("descripcion") or "").strip()
            if not desc or anio == 0:
                continue

            estado = (d.get("estado") or "").strip()
            fecha_aper = d.get("fechaApertura") or ""

            # Filtro: licitaciones activas ('Licitandose') o con apertura futura/hoy
            es_activa = estado.lower() == "licitandose" or (fecha_aper and fecha_aper[:10] >= hoy)
            if not es_activa:
                continue

            resultados.append(self._mapear_licitacion(d))

        return resultados

    def _mapear_licitacion(self, d: dict[str, Any]) -> Licitacion:
        lic_id = str(d["id"])
        num_lic = d.get("numLic")
        anio = d.get("anio")
        tipo_nombre = (d.get("tipoLic") or {}).get("nombre") or "Licitación Pública"

        numero_fmt = f"{tipo_nombre} N° {num_lic}/{anio}"

        # Apertura (fecha + hora + lugar)
        partes_apertura = []
        fecha_aper = d.get("fechaApertura")
        if fecha_aper:
            try:
                # Viene en formato "2026-11-04T03:00:00"
                dt = datetime.fromisoformat(fecha_aper.replace("Z", ""))
                partes_apertura.append(dt.strftime("%d/%m/%Y"))
            except Exception:
                partes_apertura.append(fecha_aper[:10])

        hora_aper = d.get("horaApertura")
        if hora_aper:
            partes_apertura.append(f"{hora_aper} hs")

        lugar_aper = (d.get("lugarApertura") or {}).get("nombre")
        if lugar_aper:
            partes_apertura.append(f"- {lugar_aper}")

        apertura_str = " ".join(partes_apertura) if partes_apertura else NO_INFORMADO

        # Presupuesto
        presupuesto_val = d.get("presupuesto")
        if presupuesto_val and float(presupuesto_val) > 0:
            presupuesto_str = f"$ {float(presupuesto_val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            presupuesto_str = "Ver detalle de lotes en la descripción"

        # Consulta y pliegos
        lugar_cons = (d.get("lugarConsulta") or {}).get("nombre") or NO_INFORMADO

        # Campos extras útiles
        extra = {}
        if d.get("estado"):
            extra["Estado"] = d["estado"]

        entidad = (d.get("entidadFinanciera") or {}).get("nombre")
        if entidad and entidad != "null":
            extra["Financiamiento"] = entidad

        plazo = d.get("plazo")
        if plazo:
            extra["Plazo de obra"] = f"{plazo} días"

        partidos = d.get("partido")
        if partidos and isinstance(partidos, list):
            nombres_p = [p.get("nombre") for p in partidos if p.get("nombre")]
            if nombres_p:
                extra["Partidos"] = ", ".join(nombres_p)

        return Licitacion(
            fuente=self.clave,
            id_fuente=lic_id,
            organismo=self.nombre,
            numero=numero_fmt,
            objeto=d.get("descripcion", "").strip(),
            link=self.url,
            presupuesto_oficial=presupuesto_str,
            recepcion_ofertas=NO_INFORMADO,
            apertura=apertura_str,
            valor_pliego="Sin cargo (Pliego digital)",
            lugar_consulta=lugar_cons,
            extra=extra,
        )
