"""Fuente: Boletín Oficial de la Ciudad Autónoma de Buenos Aires (BOCBA).

Consume la API REST oficial del Boletín Oficial de CABA (obtenerBoletin/0/true),
filtra los llamados a Licitación de Obra Pública y Licitación Pública de infraestructura,
y extrae del PDF oficial (vía zlib de librería estándar) la fecha de apertura,
presupuesto oficial, valor del pliego y expediente.
URL Oficial: https://boletinoficial.buenosaires.gob.ar/
"""

from __future__ import annotations

import logging
import re
import zlib
from datetime import datetime
from zoneinfo import ZoneInfo

from ..modelo import NO_INFORMADO, Licitacion
from .aspnet_comun import es_de_obra_o_arquitectura, parsear_fecha_apertura
from .base import EstructuraCambiada, Fuente, registrar

_log = logging.getLogger(__name__)
TZ_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

API_BOCBA = "https://api-restboletinoficial.buenosaires.gob.ar/obtenerBoletin/0/true"


def _extraer_texto_pdf_bocba(pdf_bytes: bytes) -> str:
    """Extrae el texto legible de un PDF FlateDecode del BOCBA sin librerías externas."""

    def _oct(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 8))
        except Exception:
            return ""

    def _limpiar(s: str) -> str:
        s = re.sub(r"\\([0-7]{3})", _oct, s)
        return s.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")

    lineas: list[str] = []
    for m in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", pdf_bytes, re.S):
        try:
            dec = zlib.decompress(m.group(1))
        except Exception:
            continue
        if b"BT" not in dec:
            continue
        txt_latin = dec.decode("latin-1", errors="ignore")
        for bloque in re.findall(r"BT(.*?)ET", txt_latin, re.S):
            tokens = [_limpiar(p[1:-1]) for p in re.findall(r"\((?:\\.|[^\\()])*\)", bloque)]
            if tokens:
                linea = "".join(tokens)
                ratio = sum(1 for c in linea if c.isalnum() or c in " .,:$0123456789/-") / max(1, len(linea))
                if ratio > 0.75:
                    lineas.append(linea.strip())
    return "\n".join(lineas)


@registrar
class BoletinOficialCaba(Fuente):
    clave = "boletin_oficial_caba"
    nombre = "Boletín Oficial CABA (BOCBA)"
    url = "https://boletinoficial.buenosaires.gob.ar/"

    def recolectar(self) -> list[Licitacion]:
        hoy = datetime.now(TZ_ARG).date()
        sesion = self.web.sesion

        try:
            resp = sesion.get(
                API_BOCBA,
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=self.web.timeout,
                verify=False,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise EstructuraCambiada(f"Error consultando API de BOCBA ({API_BOCBA}): {exc}") from exc

        normas_por_poder = data.get("normas", {}).get("normas", {})
        if not isinstance(normas_por_poder, dict):
            raise EstructuraCambiada("Estructura JSON inesperada en API de BOCBA.")

        resultados: list[Licitacion] = []
        vistos: set[str] = set()

        for _poder, tipos in normas_por_poder.items():
            if not isinstance(tipos, dict):
                continue
            for tipo_norma, reparticiones in tipos.items():
                if not isinstance(reparticiones, dict):
                    continue
                es_tipo_licitatorio = any(
                    k in tipo_norma.lower() for k in ("licitaci", "contrataci", "concurso", "obra")
                )
                if not es_tipo_licitatorio:
                    continue

                for reparticion, lista_normas in reparticiones.items():
                    if not isinstance(lista_normas, list):
                        continue
                    for norma in lista_normas:
                        if not isinstance(norma, dict):
                            continue
                        nombre_norma = str(norma.get("nombre") or "").strip()
                        sumario = str(norma.get("sumario") or "").strip()
                        id_norma = str(norma.get("id_norma") or "").strip()
                        url_norma = str(norma.get("url_norma") or "").strip()

                        if not id_norma or id_norma in vistos:
                            continue

                        if any(
                            x in nombre_norma.lower()
                            for x in ("adjudicaci", "preadjudicaci", "acta de apertura", "desiert", "fracasad", "deja sin efecto")
                        ):
                            continue

                        es_obra_explicita = "obra" in tipo_norma.lower()
                        if not es_obra_explicita and not es_de_obra_o_arquitectura(f"{nombre_norma} {sumario}"):
                            continue

                        vistos.add(id_norma)

                        presupuesto = NO_INFORMADO
                        apertura_str = NO_INFORMADO
                        valor_pliego = NO_INFORMADO
                        expediente = ""

                        if url_norma:
                            try:
                                r_pdf = sesion.get(url_norma, timeout=10, verify=False)
                                if r_pdf.status_code == 200 and r_pdf.content.startswith(b"%PDF"):
                                    texto_pdf = _extraer_texto_pdf_bocba(r_pdf.content)
                                    m_pres = re.search(
                                        r"Presupuesto\s*Oficial:\s*(\$\s*[\d.,]+|[A-Za-z]+\s+[\d.,]+)",
                                        texto_pdf,
                                        re.IGNORECASE,
                                    )
                                    if m_pres:
                                        presupuesto = m_pres.group(1).strip().rstrip(".")

                                    m_ap = re.search(
                                        r"Fecha(?:\s*y\s*Hora)?\s*de\s*Apertura(?:\s*de\s*Ofertas)?:\s*([^\n.]+)",
                                        texto_pdf,
                                        re.IGNORECASE,
                                    )
                                    if m_ap:
                                        apertura_str = re.sub(r"\s+", " ", m_ap.group(1)).strip()

                                    m_pliego = re.search(
                                        r"Valor\s*del\s*Pliego:\s*([^\n.]+)", texto_pdf, re.IGNORECASE
                                    )
                                    if m_pliego:
                                        valor_pliego = re.sub(r"\s+", " ", m_pliego.group(1)).strip()

                                    m_exp = re.search(
                                        r"Expediente(?:\s*Electrónico)?:\s*(EX-[\d\w\-\s]+?)(?:\s{2,}|\n|\.|Llámase|$)",
                                        texto_pdf,
                                        re.IGNORECASE,
                                    )
                                    if m_exp:
                                        expediente = re.sub(r"\s+", "", m_exp.group(1)).strip()
                            except Exception as exc:
                                _log.debug("No se pudo extraer PDF de BOCBA %s: %s", url_norma, exc)

                        if apertura_str != NO_INFORMADO:
                            f_dt = parsear_fecha_apertura(apertura_str)
                            if f_dt and f_dt < hoy:
                                continue

                        numero = f"{nombre_norma} ({expediente})" if expediente else nombre_norma
                        resultados.append(
                            Licitacion(
                                fuente=self.clave,
                                id_fuente=id_norma,
                                organismo=f"BOCBA - {reparticion}",
                                numero=numero,
                                objeto=sumario or nombre_norma,
                                link=url_norma or self.url,
                                presupuesto_oficial=presupuesto,
                                apertura=apertura_str,
                                valor_pliego=valor_pliego,
                            )
                        )

        return resultados
