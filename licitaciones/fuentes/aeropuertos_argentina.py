"""Fuente: Aeropuertos Argentina (AA2000) - Licitaciones de Obras e Infraestructura Aeroportuaria.

Consume el endpoint oficial Azure Front Door del portal Next.js de Aeropuertos Argentina
enviando las cabeceras de origen requeridas.
URL Oficial: https://www.aeropuertosargentina.com/es/sobre-nosotros/licitaciones
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

API_TENDERS = "https://WebAA-API-h4d5amdfcze7hthn.a02.azurefd.net/web-prod/v1/api-aa/tenders"


def _parsear_iso_aa(valor: object) -> tuple[str, datetime | None]:
    if not valor or valor == 1:
        return NO_INFORMADO, None
    texto = str(valor).strip()
    if texto.startswith("1900-"):
        return NO_INFORMADO, None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(texto[:19], fmt)
            return dt.strftime("%d/%m/%Y %H:%M hs"), dt
        except ValueError:
            continue
    return texto, None


@registrar
class AeropuertosArgentina(Fuente):
    clave = "aeropuertos_argentina"
    nombre = "Aeropuertos Argentina (AA2000)"
    url = "https://www.aeropuertosargentina.com/es/sobre-nosotros/licitaciones"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                API_TENDERS,
                headers={
                    "Accept": "application/json",
                    "Origin": "https://www.aeropuertosargentina.com",
                    "Referer": "https://www.aeropuertosargentina.com/",
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            items = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error consultando API de Aeropuertos Argentina ({API_TENDERS}): {exc}") from exc

        if not isinstance(items, list):
            raise EstructuraCambiada("La API de Aeropuertos Argentina no devolvió una lista JSON.")

        resultados: list[Licitacion] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            ap_str, ap_dt = _parsear_iso_aa(item.get("DT_FechaHoraPropuesta"))
            if not ap_dt or ap_dt.date() < hoy:
                continue

            titulo = str(item.get("DS_ObraPropuesta") or "").strip()
            desc = str(item.get("DS_DescripcionTipoPropuesta") or "").strip()
            modalidad = str(item.get("DS_NombreTipoPropuesta") or "").strip()
            if not titulo:
                continue

            if not es_de_obra_o_arquitectura(f"{titulo} {desc} {modalidad}"):
                continue

            id_pub = str(item.get("ID_Publicacion") or "")
            nro_prop = str(item.get("NU_Propuesta") or id_pub).strip()
            numero = f"Propuesta N° {nro_prop} ({modalidad})" if modalidad else f"Propuesta N° {nro_prop}"

            pres_val = item.get("NU_PresupuestoOficial")
            presupuesto = NO_INFORMADO
            try:
                if pres_val and float(pres_val) > 0:
                    entero, dec = f"{float(pres_val):,.2f}".split(".")
                    presupuesto = f"$ {entero.replace(',', '.')},{dec}"
            except Exception:
                pass

            link_doc = str(item.get("DS_DocumentacionLink") or "").strip()
            archivos = item.get("ArchivosPublicacion") or []
            if not link_doc and archivos and isinstance(archivos, list):
                primero = archivos[0]
                if isinstance(primero, dict) and primero.get("ID_Archivo"):
                    ext = primero.get("DS_Extension") or ".pdf"
                    link_doc = f"http://media.corpam.com.ar/licitaciones/{id_pub}_{primero['ID_Archivo']}{ext}"
            if not link_doc:
                link_doc = self.url

            responsables = item.get("ResponsablesPublicacion") or []
            consultas = []
            for r in responsables:
                if isinstance(r, dict):
                    nom = r.get("DS_Nombre") or ""
                    mail = r.get("DS_Email") or ""
                    if mail:
                        consultas.append(f"{nom} ({mail})".strip())

            rec_str, _ = _parsear_iso_aa(item.get("DT_FechaHoraLimiteOfertas"))

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=id_pub or nro_prop,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=titulo,
                    link=link_doc,
                    presupuesto_oficial=presupuesto,
                    recepcion_ofertas=rec_str,
                    apertura=ap_str,
                    lugar_consulta=", ".join(consultas) if consultas else NO_INFORMADO,
                )
            )

        return resultados
