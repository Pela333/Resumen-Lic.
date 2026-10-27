"""Fuente: CONTRAT.AR - Portal Electrónico de Contratación de Obra Pública Nacional.

Portal oficial del Gobierno Nacional exclusivo para licitaciones y contratos de obra pública
(viales, civiles, ferroviarias, portuarias, infraestructura y arquitectura).
URL Oficial: https://contratar.gob.ar/ListarAperturaProxima.aspx
"""

from __future__ import annotations

import logging
from bs4 import BeautifulSoup

from ..modelo import Licitacion
from .aspnet_comun import fecha_hoy_arg, parsear_fecha_apertura, resolver_link_pliego
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)


@registrar
class Contratar(Fuente):
    clave = "contratar"
    nombre = "CONTRAT.AR - Obra Pública Nacional"
    url = "https://contratar.gob.ar/ListarAperturaProxima.aspx"

    def recolectar(self) -> list[Licitacion]:
        hoy = fecha_hoy_arg()
        sesion = self.web.sesion

        # 1. Visita previa a Default.aspx para inicializar la sesión en el servidor ASP.NET
        try:
            sesion.get("https://contratar.gob.ar/Default.aspx", timeout=self.web.timeout)
        except Exception as exc:
            _log.warning("No se pudo contactar Default.aspx de CONTRAT.AR: %s", exc)

        # 2. Obtiene el listado de próximas aperturas
        respuesta = sesion.get(self.url, timeout=self.web.timeout)
        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegos")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla 'ctl00_CPH1_GridListaPliegos' en CONTRAT.AR.")

        # Extrae datos de ViewState para resolver links de pliego ciudadano por postback
        viewstate_tag = soup.find("input", {"id": "__VIEWSTATE"})
        viewstate = viewstate_tag["value"] if viewstate_tag else ""
        viewstategen_tag = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
        viewstategen = viewstategen_tag["value"] if viewstategen_tag else ""
        eventval_tag = soup.find("input", {"id": "__EVENTVALIDATION"})
        eventval = eventval_tag["value"] if eventval_tag else ""

        filas = tabla.find_all("tr")[1:]  # Saltea encabezado
        resultados: list[Licitacion] = []

        for i, fila in enumerate(filas):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            if len(celdas) < 6:
                continue

            numero = celdas[0]
            # Saltea filas de paginador
            if numero.isdigit() or "..." in numero:
                continue

            objeto = celdas[1]
            tipo = celdas[2]
            fecha_str = celdas[3]
            estado = celdas[4]
            unidad = celdas[5]

            # Solo licitaciones vigentes/publicadas
            if estado.lower() not in ["publicado", "vigente", "abierto"]:
                continue

            fecha_dt = parsear_fecha_apertura(fecha_str)
            if fecha_dt is None or fecha_dt < hoy:
                continue

            # Resuelve enlace público al pliego ciudadano si está disponible
            link = self.url
            if viewstate:
                target = f"ctl00$CPH1$GridListaPliegos$ctl{i+2:02d}$lnkNumeroProceso"
                pliego_link = resolver_link_pliego(
                    sesion, self.url, target, viewstate, viewstategen, eventval
                )
                if pliego_link:
                    link = pliego_link

            organismo = f"CONTRAT.AR - {unidad}" if unidad else self.nombre

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=organismo,
                    numero=numero,
                    objeto=objeto,
                    link=link,
                    apertura=fecha_str,
                    extra={"Tipo de Proceso": tipo, "Estado": estado},
                )
            )

        return resultados
