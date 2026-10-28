"""Arma el resumen en dos formatos: HTML (cuerpo del mail) y PDF (adjunto)."""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .modelo import Licitacion

# Campos que se muestran, en orden (de PREGUNTAS.md, sección 2)
CAMPOS = [
    ("Número", "numero"),
    ("Objeto", "objeto"),
    ("Presupuesto oficial", "presupuesto_oficial"),
    ("Recepción de ofertas", "recepcion_ofertas"),
    ("Acto de apertura", "apertura"),
    ("Valor del pliego", "valor_pliego"),
    ("Consulta de pliegos", "lugar_consulta"),
]


@dataclass
class EstadoFuente:
    clave: str
    nombre: str
    url: str
    estado: str          # 'ok' o 'error'
    visibles: int = 0
    nuevas: int = 0
    mensaje: str = ""
    racha: int = 0       # consultas seguidas en error o con 0 resultados
    alerta: bool = False

    def descripcion(self) -> str:
        if self.estado == "error":
            return f"ERROR - No se pudo acceder o cambió el formato ({self.mensaje})"
        return f"OK - {self.visibles} activa(s), {self.nuevas} nueva(s)"


def _resumen(lics: list[Licitacion]) -> str:
    if not lics:
        return "No se encontraron licitaciones nuevas desde el último envío."
    por_org: dict[str, int] = {}
    for lic in lics:
        por_org[lic.organismo] = por_org.get(lic.organismo, 0) + 1
    detalle = "; ".join(f"{n} de {org}" for org, n in por_org.items())
    plural = "licitación nueva" if len(lics) == 1 else "licitaciones nuevas"
    return f"{len(lics)} {plural} ({detalle})"


# ----------------------------------------------------------------- HTML (mail)

def generar_html(lics: list[Licitacion], estados: list[EstadoFuente], fecha: str) -> str:
    e = html.escape
    tarjetas = []
    for lic in lics:
        filas = "".join(
            f'<tr><td style="padding:4px 12px 4px 0;color:#5b6472;vertical-align:top;white-space:nowrap">{e(etq)}</td>'
            f'<td style="padding:4px 0;color:#1d2433">{e(getattr(lic, campo))}</td></tr>'
            for etq, campo in CAMPOS
        )
        filas += "".join(
            f'<tr><td style="padding:4px 12px 4px 0;color:#5b6472;vertical-align:top">{e(k)}</td>'
            f'<td style="padding:4px 0;color:#1d2433">{e(v)}</td></tr>'
            for k, v in lic.extra.items()
        )
        tarjetas.append(f"""
        <div style="border:1px solid #dde3ec;border-left:5px solid #0b5cad;border-radius:8px;padding:16px;margin:0 0 16px">
          <div style="font-size:12px;color:#0b5cad;font-weight:bold;text-transform:uppercase">{e(lic.organismo)}</div>
          <table style="border-collapse:collapse;font-size:14px;margin-top:8px">{filas}</table>
          <a href="{e(lic.link)}" style="display:inline-block;margin-top:10px;background:#0b5cad;color:#fff;
             text-decoration:none;padding:8px 14px;border-radius:6px;font-size:13px">Ver publicación oficial</a>
        </div>""")

    filas_estado = "".join(
        f'<tr><td style="padding:6px 10px;border-top:1px solid #eef1f5">'
        f'<a href="{e(s.url)}" style="color:#1d2433">{e(s.nombre)}</a></td>'
        f'<td style="padding:6px 10px;border-top:1px solid #eef1f5;'
        f'color:{"#b42318" if s.estado == "error" or s.alerta else "#067647"}">{e(s.descripcion())}</td></tr>'
        for s in estados
    )
    hay_problemas = any(s.estado == "error" or s.alerta for s in estados)
    aviso = ("" if not hay_problemas else
             '<div style="background:#fef3f2;border:1px solid #fecdca;color:#b42318;padding:12px;border-radius:8px;'
             'margin-bottom:16px;font-size:14px"><b>Atención:</b> una o más fuentes no pudieron revisarse bien. '
             'Ver "Estado de las fuentes" al final.</div>')

    return f"""<!DOCTYPE html><html><body style="margin:0;background:#f4f6f9;font-family:Segoe UI,Arial,sans-serif">
<div style="max-width:680px;margin:0 auto;padding:20px">
  <div style="background:#0f2747;color:#fff;border-radius:10px 10px 0 0;padding:20px">
    <div style="font-size:20px;font-weight:bold">Resumen de licitaciones</div>
    <div style="font-size:13px;opacity:.8">{e(fecha)}</div>
  </div>
  <div style="background:#fff;border-radius:0 0 10px 10px;padding:20px">
    {aviso}
    <p style="font-size:15px;color:#1d2433;margin-top:0"><b>{e(_resumen(lics))}</b></p>
    {"".join(tarjetas)}
    <h3 style="font-size:15px;color:#1d2433;margin:24px 0 8px">Estado de las fuentes</h3>
    <table style="border-collapse:collapse;width:100%;font-size:13px">{filas_estado}</table>
    <p style="font-size:12px;color:#8a93a3;margin-top:20px">
      Los datos se copian textualmente de cada sitio oficial; verificar siempre en el enlace original.
      El detalle completo va en el PDF adjunto.</p>
  </div>
</div></body></html>"""


def generar_texto(lics: list[Licitacion], estados: list[EstadoFuente], fecha: str) -> str:
    """Versión en texto plano, para clientes de correo que no muestran HTML."""
    lineas = [f"Resumen de licitaciones - {fecha}", "", _resumen(lics), ""]
    for lic in lics:
        lineas.append(f"== {lic.organismo} ==")
        lineas += [f"{etq}: {getattr(lic, campo)}" for etq, campo in CAMPOS]
        lineas += [f"{k}: {v}" for k, v in lic.extra.items()]
        lineas += [f"Enlace: {lic.link}", ""]
    lineas.append("Estado de las fuentes:")
    lineas += [f"- {s.nombre}: {s.descripcion()}" for s in estados]
    return "\n".join(lineas)


# ----------------------------------------------------------------- PDF (adjunto)

_FUENTES_TTF = [  # (normal, negrita). Se usa la primera que exista en la máquina.
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]

_REEMPLAZOS_LATIN1 = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "•": "-"}


class _PDF(FPDF):
    def __init__(self, fecha: str) -> None:
        super().__init__(format="A4")
        self.fecha = fecha
        self.unicode = False
        for normal, negrita in _FUENTES_TTF:
            if os.path.exists(normal) and os.path.exists(negrita):
                self.add_font("Base", "", normal)
                self.add_font("Base", "B", negrita)
                self.unicode = True
                break
        self.familia = "Base" if self.unicode else "Helvetica"
        self.set_auto_page_break(True, margin=18)
        self.set_margins(15, 15, 15)

    def t(self, texto: str) -> str:
        """Si no hay fuente Unicode disponible, adapta caracteres especiales."""
        if self.unicode:
            return texto
        for a, b in _REEMPLAZOS_LATIN1.items():
            texto = texto.replace(a, b)
        return texto.encode("latin-1", "replace").decode("latin-1")

    def header(self) -> None:
        self.set_fill_color(15, 39, 71)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(15, 6)
        self.set_text_color(255, 255, 255)
        self.set_font(self.familia, "B", 14)
        self.cell(0, 6, self.t("Resumen de licitaciones"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self.familia, "", 9)
        self.cell(0, 5, self.t(self.fecha))
        self.set_text_color(29, 36, 51)
        self.set_y(28)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self.familia, "", 8)
        self.set_text_color(138, 147, 163)
        self.cell(0, 5, self.t(f"Datos copiados textualmente de los sitios oficiales. Página {self.page_no()}"),
                  align="C")

    def fila(self, etiqueta: str, valor: str) -> None:
        self.set_font(self.familia, "B", 9)
        self.set_text_color(91, 100, 114)
        self.cell(42, 5.5, self.t(etiqueta))
        self.set_font(self.familia, "", 9)
        self.set_text_color(29, 36, 51)
        self.multi_cell(0, 5.5, self.t(valor), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def generar_pdf(lics: list[Licitacion], estados: list[EstadoFuente], fecha: str, destino: Path) -> Path:
    pdf = _PDF(fecha)
    pdf.add_page()
    pdf.set_font(pdf.familia, "B", 11)
    pdf.multi_cell(0, 6, pdf.t(_resumen(lics)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    for lic in lics:
        if pdf.get_y() > pdf.h - 70:
            pdf.add_page()
        pdf.set_fill_color(234, 241, 251)
        pdf.set_font(pdf.familia, "B", 10)
        pdf.set_text_color(11, 92, 173)
        pdf.cell(0, 7, pdf.t(lic.organismo), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        for etq, campo in CAMPOS:
            pdf.fila(etq, getattr(lic, campo))
        for k, v in lic.extra.items():
            pdf.fila(k, v)
        pdf.set_font(pdf.familia, "B", 9)
        pdf.set_text_color(91, 100, 114)
        pdf.cell(42, 5.5, pdf.t("Enlace"))
        pdf.set_font(pdf.familia, "", 9)
        pdf.set_text_color(11, 92, 173)
        pdf.write(5.5, pdf.t(lic.link), link=lic.link)
        pdf.ln(10)

    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    pdf.set_text_color(29, 36, 51)
    pdf.set_font(pdf.familia, "B", 11)
    pdf.cell(0, 7, pdf.t("Estado de las fuentes"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for s in estados:
        if pdf.get_y() > pdf.h - 25:
            pdf.add_page()
        problema = s.estado == "error" or s.alerta
        pdf.set_font(pdf.familia, "B", 9)
        pdf.set_text_color(29, 36, 51)
        pdf.multi_cell(0, 5.5, pdf.t(s.nombre), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(pdf.familia, "", 9)
        pdf.set_text_color(*((180, 35, 24) if problema else (6, 118, 71)))
        pdf.multi_cell(0, 5.5, pdf.t(s.descripcion()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino
