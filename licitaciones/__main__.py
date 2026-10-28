"""Punto de entrada: recolecta, guarda, arma el resumen y lo envía.

Uso:
    python -m licitaciones               corrida completa (envía el mail si hay credenciales en .env)
    python -m licitaciones --sin-enviar  genera PDF y HTML en /salida sin enviar ni marcar nada como enviado
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from . import correo, reporte
from .basedatos import BaseDatos
from .fuentes import REGISTRO, EstructuraCambiada
from .web import ClienteWeb

RAIZ = Path(__file__).resolve().parent.parent
log = logging.getLogger("licitaciones")


def _configurar_log(carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(carpeta / "ejecucion.log", encoding="utf-8")],
    )
    logging.getLogger("fontTools").setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resumen automático de licitaciones")
    parser.add_argument("--sin-enviar", action="store_true",
                        help="Genera el reporte pero no envía el mail ni marca licitaciones como enviadas")
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")
    cfg = tomllib.loads((RAIZ / "config.toml").read_text(encoding="utf-8"))
    load_dotenv(RAIZ / ".env")

    ruta_db_real = RAIZ / cfg["general"]["base_de_datos"]
    _configurar_log(ruta_db_real.parent)
    zona = ZoneInfo(cfg["general"]["zona_horaria"])
    ahora = datetime.now(zona)
    marca = ahora.isoformat(timespec="seconds")
    fecha_legible = ahora.strftime("%d/%m/%Y %H:%M")

    if args.sin_enviar:
        import shutil
        salida_tmp = RAIZ / cfg["general"]["carpeta_salida"]
        salida_tmp.mkdir(parents=True, exist_ok=True)
        ruta_db = salida_tmp / "test_temp.db"
        if ruta_db_real.exists():
            shutil.copy2(ruta_db_real, ruta_db)
        elif ruta_db.exists():
            ruta_db.unlink()
    else:
        ruta_db = ruta_db_real

    db = BaseDatos(ruta_db)
    web = ClienteWeb()
    umbral = int(cfg["alertas"]["corridas_sin_resultados_para_avisar"])

    # 1) Recolectar cada fuente por separado: si una falla, las demás siguen.
    estados: list[reporte.EstadoFuente] = []
    for clave in cfg["fuentes"]["activas"]:
        clase = REGISTRO.get(clave)
        if clase is None:
            log.error("Fuente '%s' en config.toml no existe en el código", clave)
            continue
        fuente = clase(web)
        estado = reporte.EstadoFuente(clave=clave, nombre=fuente.nombre, url=fuente.url, estado="ok")
        try:
            encontradas = fuente.recolectar()
            estado.visibles = len(encontradas)
            estado.nuevas = sum(db.guardar(lic, marca) for lic in encontradas)
            log.info("%s: %d visibles, %d nuevas", clave, estado.visibles, estado.nuevas)
        except EstructuraCambiada as exc:
            estado.estado, estado.mensaje = "error", f"la página cambió de estructura ({exc})"
            log.error("%s: %s", clave, estado.mensaje)
        except Exception as exc:  # caída, timeout, bloqueo, etc.
            estado.estado, estado.mensaje = "error", f"{type(exc).__name__}: {exc}"
            log.exception("%s: error al recolectar", clave)
        db.registrar_consulta(clave, marca, estado.estado, estado.visibles, estado.nuevas, estado.mensaje)
        estado.racha = db.racha_sin_resultados(clave)
        # Solo marcamos alerta si hubo un fallo real de acceso o lectura en la fuente,
        # no cuando el organismo simplemente tiene 0 licitaciones activas vigentes.
        estado.alerta = estado.estado == "error"
        estados.append(estado)

    # 2) Armar el resumen con todo lo que todavía no se envió.
    pendientes = db.pendientes()
    hay_problemas = any(s.estado == "error" or s.alerta for s in estados)
    if not pendientes and not hay_problemas and not cfg["mail"]["enviar_si_no_hay_novedades"]:
        log.info("Sin novedades; no se envía mail (según config.toml)")
        return 0

    salida = RAIZ / cfg["general"]["carpeta_salida"]
    salida.mkdir(parents=True, exist_ok=True)
    nombre = f"licitaciones_{ahora.strftime('%Y-%m-%d_%H%M')}"
    html = reporte.generar_html(pendientes, estados, fecha_legible)
    texto = reporte.generar_texto(pendientes, estados, fecha_legible)
    (salida / f"{nombre}.html").write_text(html, encoding="utf-8")
    pdf = reporte.generar_pdf(pendientes, estados, fecha_legible, salida / f"{nombre}.pdf")
    log.info("Reporte generado: %s (%d licitaciones)", pdf, len(pendientes))

    # 3) Enviar. Solo si el envío sale bien se marcan como enviadas.
    if args.sin_enviar:
        log.info("Modo --sin-enviar: no se envió el mail ni se marcó nada como enviado")
        return 0
    destinatarios = [d.strip() for d in os.getenv("MAIL_DESTINATARIOS", "").split(",") if d.strip()]
    try:
        correo.enviar(
            usuario=os.getenv("GMAIL_USUARIO", "").strip(),
            clave=os.getenv("GMAIL_CLAVE_APLICACION", "").strip(),
            destinatarios=destinatarios,
            asunto=cfg["mail"]["asunto"].format(fecha=ahora.strftime("%d/%m/%Y")),
            texto=texto, html=html, pdf=pdf,
        )
    except correo.FaltanCredenciales as exc:
        log.warning("%s. El reporte quedó guardado en %s", exc, salida)
        return 2
    except Exception:
        log.exception("Falló el envío del mail; las licitaciones quedan pendientes para el próximo envío")
        return 1
    db.marcar_enviadas([lic.uid for lic in pendientes], marca)
    log.info("Mail enviado a %s", ", ".join(destinatarios))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
