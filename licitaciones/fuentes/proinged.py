"""Fuente: PROINGED - Programa de Generación Eléctrica Distribuida de la Provincia de Buenos Aires.

Monitorea licitaciones de construcción de parques solares fotovoltaicos, generación distribuida,
líneas eléctricas, bombeo solar y eficiencia energética en PBA.
URL Oficial: https://www.proinged.org.ar/licitaciones/
"""

from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)


@registrar
class Proinged(Fuente):
    clave = "proinged"
    nombre = "PROINGED - Generación Eléctrica Distribuida PBA"
    url = "https://www.proinged.org.ar/licitaciones/"

    def recolectar(self) -> list[Licitacion]:
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise EstructuraCambiada(f"Error conectando con PROINGED: {exc}") from exc

        soup = BeautifulSoup(resp.text, "html.parser")
        headings = soup.find_all(["h2", "h3", "h4", "h5"])
        lic_headings = [h for h in headings if "licitación proinged" in h.get_text().lower()]

        if not lic_headings:
            raise EstructuraCambiada("No se encontraron encabezados de licitaciones en PROINGED.")

        resultados: list[Licitacion] = []

        for h in lic_headings:
            titulo = h.get_text(strip=True)
            parent = h.find_parent("div")
            txt_parent = parent.get_text(" | ", strip=True) if parent else ""

            # PROINGED categoriza explícitamente en el texto del bloque como "Vigente" o "Finalizada"
            if "vigente" not in txt_parent.lower():
                continue

            m_num = re.search(r"licitaci[oó]n proinged\s+([0-9\-/]+)", titulo, re.IGNORECASE)
            numero = f"Licitación {m_num.group(1)}" if m_num else titulo[:30]

            # Objeto de la licitación
            m_obj = re.search(r'["“](.*?)["”]', titulo)
            objeto = m_obj.group(1).strip() if m_obj else titulo

            # Buscar enlace a pre-pliego o circular si existe
            a_link = parent.find("a", href=True) if parent else None
            link = a_link["href"] if a_link else self.url

            resultados.append(
                Licitacion(
                    fuente=self.clave,
                    id_fuente=numero,
                    organismo=self.nombre,
                    numero=numero,
                    objeto=objeto,
                    link=link,
                    presupuesto_oficial=NO_INFORMADO,
                    apertura="Pliego Vigente",
                    extra={"Estado": "Vigente"},
                )
            )

        return resultados
