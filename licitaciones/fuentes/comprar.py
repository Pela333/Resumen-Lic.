"""Fuente: COMPR.AR - Portal de Contrataciones de la Administración Nacional.

Portal general de compras de bienes y servicios del Estado Nacional.
Filtra licitaciones vinculadas a adecuaciones edilicias, obras de infraestructura,
instalaciones y mantenimiento mayor de dependencias nacionales.
URL Oficial: https://comprar.gob.ar/Compras.aspx?qs=W1HXHGHtH10=
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
class Comprar(Fuente):
    clave = "comprar"
    nombre = "COMPR.AR - Contrataciones Estado Nacional"
    url = "https://comprar.gob.ar/Compras.aspx?qs=W1HXHGHtH10="

    def recolectar(self) -> list[Licitacion]:
        hoy = fecha_hoy_arg()
        sesion = self.web.sesion

        respuesta = sesion.get(self.url, timeout=self.web.timeout)
        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegosAperturaProxima")
        if not tabla:
            raise EstructuraCambiada(
                "No se encontró la tabla 'ctl00_CPH1_GridListaPliegosAperturaProxima' en COMPR.AR."
            )

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

            # En portal generalista nacional, se filtran las licitaciones pertinentes de obra/infraestructura
            if not es_de_obra_o_arquitectura(objeto):
                continue

            link = self.url
            if viewstate:
                target = f"ctl00$CPH1$GridListaPliegosAperturaProxima$ctl{i+2:02d}$lnkNumeroProceso"
                pliego_link = resolver_link_pliego(
                    sesion, self.url, target, viewstate, viewstategen, eventval
                )
                if pliego_link:
                    link = pliego_link

            organismo = f"Nación - {unidad}" if unidad else self.nombre

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
