"""Fuente: BA Obras - Sistema de Contrataciones de Obra Pública de la Ciudad de Buenos Aires.

Portal oficial del Gobierno de la Ciudad Autónoma de Buenos Aires (DGUIAF / GCBA)
exclusivo para obras de arquitectura, salud, escuelas, viales y espacio público.
URL Oficial: https://buenosairesobras.dguiaf-gcba.gov.ar/ListarAperturaProxima.aspx
"""

from __future__ import annotations

import logging
from bs4 import BeautifulSoup

from ..modelo import Licitacion
from .aspnet_comun import fecha_hoy_arg, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)


@registrar
class BaObras(Fuente):
    clave = "ba_obras"
    nombre = "BA Obras - Obra Pública Ciudad de Buenos Aires"
    url = "https://buenosairesobras.dguiaf-gcba.gov.ar/ListarAperturaProxima.aspx"

    def recolectar(self) -> list[Licitacion]:
        hoy = fecha_hoy_arg()
        sesion = self.web.sesion

        # BA Obras opera detrás de balanceador BIG-IP y requiere capturar la cookie de sesión ASP.NET
        # sin seguir el redirect a Default.aspx (que reinicia la cookie).
        sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta = sesion.get(self.url, allow_redirects=False, timeout=self.web.timeout)
        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tabla = soup.find("table", id="ctl00_CPH1_GridListaPliegos")
        if not tabla:
            raise EstructuraCambiada("No se encontró la tabla 'ctl00_CPH1_GridListaPliegos' en BA Obras.")

        filas = tabla.find_all("tr")[1:]  # Saltea encabezado
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
