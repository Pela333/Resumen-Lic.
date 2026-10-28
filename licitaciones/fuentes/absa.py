"""Fuente: ABSA (Aguas Bonaerenses S.A.) - Portal de Proveedores.

Consume la API JSON pública de invitados del portal Angular de ABSA para extraer
concursos y licitaciones vigentes de obras de agua, saneamiento e infraestructura.
URL Oficial: https://proveedores.aguasbonaerenses.com.ar/#/guest
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

API_GUEST = "https://proveedores-back.aguasbonaerenses.com.ar/api/licitacion/lista_guest"


def _formatear_fecha_iso(valor: str | None) -> tuple[str, datetime | None]:
    if not valor:
        return NO_INFORMADO, None
    texto = str(valor).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(texto[:19], fmt)
            return dt.strftime("%d/%m/%Y %H:%M hs"), dt
        except ValueError:
            continue
    return texto, None


def _formatear_monto(valor: object) -> str:
    if valor in (None, "", 0, "0", "0.00"):
        return NO_INFORMADO
    try:
        num = float(str(valor))
        if num <= 0:
            return NO_INFORMADO
        entero, dec = f"{num:,.2f}".split(".")
        entero_ar = entero.replace(",", ".")
        return f"$ {entero_ar},{dec}"
    except Exception:
        return str(valor)


@registrar
class Absa(Fuente):
    clave = "absa"
    nombre = "ABSA - Aguas Bonaerenses S.A."
    url = "https://proveedores.aguasbonaerenses.com.ar/#/guest"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                API_GUEST,
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            items = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error consultando API de ABSA ({API_GUEST}): {exc}") from exc

        if not isinstance(items, list):
            raise EstructuraCambiada("La API de ABSA no devolvió una lista JSON válida.")

        resultados: list[Licitacion] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("anuladadesiertafracasada") is not None:
                continue

            ap_str, ap_dt = _formatear_fecha_iso(item.get("fechaapertura"))
            if not ap_dt or ap_dt.date() < hoy:
                continue

            titulo = str(item.get("titulo") or "").strip()
            descripcion = str(item.get("descripcion") or "").strip()
            texto_completo = f"{titulo} {descripcion}".strip()

            if not es_de_obra_o_arquitectura(texto_completo):
                continue

            id_lic = str(item.get("idlicitacion") or "")
            tipo = str(item.get("tipocontratacion") or "LICITACIÓN").strip()
            numero_raw = item.get("numero")
            anio_raw = item.get("anio")
            numero = f"{tipo} {numero_raw}/{anio_raw}" if (numero_raw and anio_raw) else f"{tipo} ID {id_lic}"

            rec_str, _ = _formatear_fecha_iso(item.get("fechalimiteofertas"))
            presupuesto = _formatear_monto(item.get("presupuestooficial"))
            objeto = f"{titulo} — {descripcion}" if (descripcion and descripcion != titulo) else titulo

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_lic or numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto[:450],
                    link=self.url,
                    presupuesto_oficial=presupuesto,
                    recepcion_ofertas=rec_str,
                    apertura=ap_str,
                )
            )

        return resultados
