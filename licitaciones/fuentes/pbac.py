"""Fuente: PBAC - Portal de Compras Electrónicas de la Provincia de Buenos Aires.

Portal general de compras y contrataciones de la Provincia de Buenos Aires.
Filtra específicamente las licitaciones vinculadas a obras públicas, infraestructura,
arquitectura, instalaciones y refacciones de edificios provinciales.
URL Oficial: https://pbac.cgp.gba.gov.ar/ListarAperturaProxima.aspx
"""

from __future__ import annotations

import logging
from bs4 import BeautifulSoup

from ..modelo import Licitacion
from .aspnet_comun import (
    es_de_obra_o_arquitectura,
    fecha_hoy_arg,
    parsear_fecha_apertura,
    resolver_link_pliego,
)
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)


@registrar
class Pbac(Fuente):
    clave = "pbac"
    nombre = "PBAC - Compras Provincia de Buenos Aires"
    url = "https://pbac.cgp.gba.gov.ar/ListarAperturaProxima.aspx"

    def recolectar(self) -> list[Licitacion]:
        hoy = fecha_hoy_arg()
        sesion = self.web.sesion

        respuesta = sesion.get(self.url, timeout=self.web.timeout)
        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegos")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla 'ctl00_CPH1_GridListaPliegos' en PBAC.")

        viewstate_tag = soup.find("input", {"id": "__VIEWSTATE"})
        viewstate = viewstate_tag["value"] if viewstate_tag else ""
        viewstategen_tag = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
        viewstategen = viewstategen_tag["value"] if viewstategen_tag else ""
        eventval_tag = soup.find("input", {"id": "__EVENTVALIDATION"})
        eventval = eventval_tag["value"] if eventval_tag else ""

        filas = tabla.find_all("tr")[1:]
        resultados: list[Licitacion] = []

        for i, fila in enumerate(filas):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            if len(celdas) < 6:
                continue

            numero = celdas[0]
            if numero.isdigit() or "..." in numero:
                continue

            objeto = celdas[1]
            tipo = celdas[2]
            fecha_str = celdas[3]
            estado = celdas[4]
            unidad = celdas[5]

            if estado.lower() not in ["publicado", "vigente", "abierto"]:
                continue

            fecha_dt = parsear_fecha_apertura(fecha_str)
            if fecha_dt is None or fecha_dt < hoy:
                continue

            # En portal generalista provincial, se filtran las licitaciones pertinentes de obra/infraestructura
            if not es_de_obra_o_arquitectura(objeto):
                continue

            link = self.url
            if viewstate:
                target = f"ctl00$CPH1$GridListaPliegos$ctl{i+2:02d}$lnkNumeroProceso"
                pliego_link = resolver_link_pliego(
                    sesion, self.url, target, viewstate, viewstategen, eventval
                )
                if pliego_link:
                    link = pliego_link

            organismo = f"PBA - {unidad}" if unidad else self.nombre

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
