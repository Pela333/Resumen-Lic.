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


MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}


def _extraer_fecha_iso(texto: str) -> str | None:
    m = re.search(r'(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})', texto.lower())
    if m:
        dia, mes_str, anio = int(m.group(1)), m.group(2), int(m.group(3))
        mes = MESES.get(mes_str)
        if mes:
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
    return None


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
        match = re.search(r'\\"items\\":\s*(\[.*?\])\s*[,}]', html_text)
        if not match:
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

        from datetime import datetime
        hoy = datetime.now().strftime("%Y-%m-%d")

        resultados: list[Licitacion] = []
        for it in items:
            estado = (it.get("estado") or "").strip().lower()
            # Descartar licitaciones que ya terminaron o están adjudicadas
            if any(k in estado for k in ["adjudicada", "finalizada", "en ejecuci"]):
                continue

            # Verificar fecha de apertura
            fecha_str = it.get("fecha_apertura") or ""
            fecha_iso = _extraer_fecha_iso(fecha_str)
            if fecha_iso and fecha_iso < hoy:
                continue

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
