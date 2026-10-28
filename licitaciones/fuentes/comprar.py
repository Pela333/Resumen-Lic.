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
        max_paginas = 15

        respuesta = sesion.get(self.url, timeout=self.web.timeout)
        respuesta.raise_for_status()

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for pagina in range(1, max_paginas + 1):
            soup = BeautifulSoup(respuesta.text, "html.parser")
            tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegosAperturaProxima")
            if not tabla:
                if pagina == 1:
                    raise EstructuraCambiada(
                        "No se encontró la tabla 'ctl00_CPH1_GridListaPliegosAperturaProxima' en COMPR.AR."
                    )
                break

            viewstate_tag = soup.find("input", {"id": "__VIEWSTATE"})
            viewstate = viewstate_tag["value"] if viewstate_tag else ""
            viewstategen_tag = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
            viewstategen = viewstategen_tag["value"] if viewstategen_tag else ""
            eventval_tag = soup.find("input", {"id": "__EVENTVALIDATION"})
            eventval = eventval_tag["value"] if eventval_tag else ""

            filas = tabla.find_all("tr")[1:]

            for i, fila in enumerate(filas):
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                if len(celdas) < 6:
                    continue

                numero = celdas[0]
                if numero.isdigit() or "..." in numero or numero in vistos:
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

                vistos.add(numero)
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

            # Avanzar a la siguiente página de la grilla ASP.NET si existe
            sig_pag = pagina + 1
            if pagina >= max_paginas or not viewstate or f"Page${sig_pag}" not in respuesta.text:
                break
            try:
                post_data = {
                    "__EVENTTARGET": "ctl00$CPH1$GridListaPliegosAperturaProxima",
                    "__EVENTARGUMENT": f"Page${sig_pag}",
                    "__VIEWSTATE": viewstate,
                    "__VIEWSTATEGENERATOR": viewstategen,
                }
                if eventval:
                    post_data["__EVENTVALIDATION"] = eventval
                respuesta = sesion.post(self.url, data=post_data, timeout=self.web.timeout)
                respuesta.raise_for_status()
            except Exception as exc:
                _log.debug("Fin de paginación en COMPR.AR pág %d: %s", sig_pag, exc)
                break

        return resultados
