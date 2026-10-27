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

        # Inicializa sesión en balanceador BIG-IP sin seguir redirección de reinicio
        sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta = sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegos")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla 'ctl00_CPH1_GridListaPliegos' en BAC.")

        filas = tabla.find_all("tr")[1:]
        resultados: list[Licitacion] = []

        for fila in filas:
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

            # En portal generalista porteño, se filtran las licitaciones pertinentes de obra/infraestructura
            if not es_de_obra_o_arquitectura(objeto):
                continue

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

        return resultados
