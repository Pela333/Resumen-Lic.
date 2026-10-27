"""Fuente: AUSA - Autopistas Urbanas S.A. (CABA).

Consume directamente los endpoints REST internos descubiertos en Next.js:
- Públicas: https://www.ausa.com.ar/api/licitaciones?tipo=1
- Privadas: https://www.ausa.com.ar/api/licitaciones?tipo=2

Extrae licitaciones vigentes (estado activo o fecha de apertura futura),
con enlace directo a la carpeta SharePoint oficial del pliego de cada obra.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

log = logging.getLogger("licitaciones.ausa")


@registrar
class Ausa(Fuente):
    clave = "ausa"
    nombre = "AUSA - Autopistas Urbanas S.A."
    url = "https://www.ausa.com.ar/proveedores/licitaciones"
    api_url = "https://www.ausa.com.ar/api/licitaciones"

    def recolectar(self) -> list[Licitacion]:
        resultados: list[Licitacion] = []
        hoy = datetime.now().strftime("%Y-%m-%d")

        # Consultar tanto Públicas (tipo=1) como Privadas (tipo=2)
        for tipo_id, tipo_nombre in [(1, "Pública"), (2, "Privada")]:
            try:
                resp = self.web.sesion.get(
                    f"{self.api_url}?tipo={tipo_id}",
                    headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                    timeout=25,
                    verify=False,
                )
                resp.raise_for_status()
                items = resp.json()
            except Exception as exc:
                raise EstructuraCambiada(f"Error consultando API de AUSA (tipo={tipo_id}): {exc}") from exc

            if not isinstance(items, list):
                continue

            for d in items:
                # Filtrar licitaciones activas:
                # estado == 1 (abiertas/en llamado) o con fecha de apertura futura/hoy
                fecha_aper = d.get("fechaApertura") or ""
                estado_id = d.get("estado")
                esta_activa = (estado_id == 1) or (fecha_aper and fecha_aper[:10] >= hoy)

                # Si ya fue adjudicada y la fecha de apertura pasó, no se reporta como novedad abierta
                if d.get("fechaAdjudicacion") and (not fecha_aper or fecha_aper[:10] < hoy):
                    continue

                if esta_activa:
                    resultados.append(self._mapear(d, tipo_nombre))

        return resultados

    def _mapear(self, d: dict[str, Any], tipo_nombre: str) -> Licitacion:
        lic_id = str(d["id"])
        nombre_num = d.get("nombre") or lic_id
        numero = f"Licitación {tipo_nombre} N° {nombre_num}"
        objeto = (d.get("descripcion") or "").strip()

        # Enlace oficial: enlace directo a los pliegos en SharePoint si existe, o el portal
        link_pliego = d.get("link") or self.url

        # Fecha y hora de apertura
        partes_apertura = []
        fecha_aper = d.get("fechaApertura")
        if fecha_aper:
            try:
                dt = datetime.fromisoformat(fecha_aper.replace("Z", ""))
                partes_apertura.append(dt.strftime("%d/%m/%Y a las %H:%M hs"))
            except Exception:
                partes_apertura.append(fecha_aper[:10])
        apertura_str = " ".join(partes_apertura) if partes_apertura else NO_INFORMADO

        # Presupuesto oficial
        monto = d.get("monto")
        presupuesto_str = monto.strip() if (monto and str(monto).strip()) else "No informado en la web"

        # Extra
        extra = {"Tipo": tipo_nombre}
        if d.get("fechaLlamado"):
            extra["Fecha de llamado"] = str(d["fechaLlamado"])[:10]

        return Licitacion(
            fuente=self.clave,
            id_fuente=lic_id,
            organismo=self.nombre,
            numero=numero,
            objeto=objeto,
            link=link_pliego,
            presupuesto_oficial=presupuesto_str,
            recepcion_ofertas=NO_INFORMADO,
            apertura=apertura_str,
            valor_pliego="Sin cargo (Pliego digital)",
            lugar_consulta="Mesa de entradas AUSA / SharePoint",
            extra=extra,
        )
