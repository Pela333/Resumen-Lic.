"""Fuente: AUSOL - Autopistas del Sol.

Extrae las licitaciones públicas de https://www.ausol.com.ar/licitaciones
aprovechando la carga estructurada de Next.js en el HTML.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..modelo import NO_INFORMADO, Licitacion
from .base import EstructuraCambiada, Fuente, registrar

log = logging.getLogger("licitaciones.ausol")


@registrar
class Ausol(Fuente):
    clave = "ausol"
    nombre = "AUSOL - Autopistas del Sol"
    url = "https://www.ausol.com.ar/licitaciones"

    def recolectar(self) -> list[Licitacion]:
        try:
            resp = self.web.sesion.get(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=25,
                verify=False,
            )
            resp.raise_for_status()
            html_text = resp.text
        except Exception as exc:
            raise EstructuraCambiada(f"Error accediendo a AUSOL: {exc}") from exc

        # Extraer el array de "items" dentro del payload de Next.js
        # Ejemplo: \"items\":[{\"id\":310,...}]
        match = re.search(r'\\"items\\":\s*(\[.*?\])\s*[,}]', html_text)
        if not match:
            # Fallback si cambia la estructura de Next.js
            match_json = re.search(r'"items":\s*(\[.*?\])\s*[,}]', html_text)
            if not match_json:
                raise EstructuraCambiada("No se encontró la lista de licitaciones en el HTML de AUSOL.")
            raw_json = match_json.group(1)
        else:
            raw_json = match.group(1).replace(r'\"', '"').replace(r'\\', '\\')

        try:
            items = json.loads(raw_json)
        except Exception as exc:
            raise EstructuraCambiada(f"Error parseando datos JSON de AUSOL: {exc}") from exc

        resultados: list[Licitacion] = []
        for it in items:
            resultados.append(self._mapear(it))

        return resultados

    def _mapear(self, d: dict[str, Any]) -> Licitacion:
        lic_id = str(d.get("id") or "")
        etiqueta = (d.get("etiqueta") or "").strip().lstrip(".")
        titulo = (d.get("titulo") or "").strip().lstrip(".")
        fecha_aper = (d.get("fecha_apertura") or "").strip()
        estado = (d.get("estado") or "").strip()
        href = d.get("href") or ""
        link = f"https://www.ausol.com.ar{href}" if href.startswith("/") else (href or self.url)

        extra = {}
        if estado:
            extra["Estado"] = estado
        if d.get("lugar"):
            extra["Lugar"] = str(d["lugar"]).strip()

        return Licitacion(
            fuente=self.clave,
            id_fuente=lic_id or etiqueta,
            organismo=self.nombre,
            numero=etiqueta or "Licitación Pública AUSOL",
            objeto=titulo,
            link=link,
            presupuesto_oficial=NO_INFORMADO,
            recepcion_ofertas=NO_INFORMADO,
            apertura=fecha_aper or NO_INFORMADO,
            valor_pliego="Pliego digital",
            lugar_consulta="Mesa de compras AUSOL",
            extra=extra,
        )
