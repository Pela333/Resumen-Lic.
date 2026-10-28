"""Fuente: BAC - Buenos Aires Compras (Portal General de Compras de la Ciudad de Buenos Aires).

Portal general de compras del Gobierno de la Ciudad Autónoma de Buenos Aires.
Filtra licitaciones orientadas a mantenimiento edilicio, instalaciones, refacciones
y adecuaciones de infraestructura urbana.
URL Oficial: https://www.buenosairescompras.gob.ar/ListarAperturaProxima.aspx
"""

from __future__ import annotations

import logging
from bs4 import BeautifulSoup

from ..modelo import Licitacion
from .aspnet_comun import (
    es_de_obra_o_arquitectura,
    fecha_hoy_arg,
    parsear_fecha_apertura,
)
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)


@registrar
class Bac(Fuente):
    clave = "bac"
    nombre = "BAC - Buenos Aires Compras"
    url = "https://www.buenosairescompras.gob.ar/ListarAperturaProxima.aspx"

    def recolectar(self) -> list[Licitacion]:
        hoy = fecha_hoy_arg()
        sesion = self.web.sesion
        max_paginas = 15

        # Inicializa sesión en balanceador BIG-IP sin seguir redirección de reinicio
        sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta = sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta.raise_for_status()

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for pagina in range(1, max_paginas + 1):
            soup = BeautifulSoup(respuesta.text, "html.parser")
            tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegos")
            if not tabla:
                if pagina == 1:
                    raise EstructuraCambiada("No se encontró la tabla 'ctl00_CPH1_GridListaPliegos' en BAC.")
                break

            viewstate_tag = soup.find("input", {"id": "__VIEWSTATE"})
            viewstate = viewstate_tag["value"] if viewstate_tag else ""
            viewstategen_tag = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
            viewstategen = viewstategen_tag["value"] if viewstategen_tag else ""
            eventval_tag = soup.find("input", {"id": "__EVENTVALIDATION"})
            eventval = eventval_tag["value"] if eventval_tag else ""

            filas = tabla.find_all("tr")[1:]

            for fila in filas:
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

                # En portal generalista porteño, se filtran las licitaciones pertinentes de obra/infraestructura
                if not es_de_obra_o_arquitectura(objeto):
                    continue

                vistos.add(numero)
                organismo = f"GCBA - {unidad}" if unidad else self.nombre

                resultados.append(
                    Licitacion(
                        fuente=self.clave,
                        id_fuente=numero,
                        organismo=organismo,
                        numero=numero,
                        objeto=objeto,
                        link=self.url,
                        apertura=fecha_str,
                        extra={"Tipo de Proceso": tipo, "Estado": estado},
                    )
                )

            sig_pag = pagina + 1
            if pagina >= max_paginas or not viewstate or f"Page${sig_pag}" not in respuesta.text:
                break
            try:
                post_data = {
                    "__EVENTTARGET": "ctl00$CPH1$GridListaPliegos",
                    "__EVENTARGUMENT": f"Page${sig_pag}",
                    "__VIEWSTATE": viewstate,
                    "__VIEWSTATEGENERATOR": viewstategen,
                }
                if eventval:
                    post_data["__EVENTVALIDATION"] = eventval
                respuesta = sesion.post(self.url, data=post_data, allow_redirects=False, timeout=self.web.timeout)
                respuesta.raise_for_status()
            except Exception as exc:
                _log.debug("Fin de paginación en BAC pág %d: %s", sig_pag, exc)
                break

        return resultados
