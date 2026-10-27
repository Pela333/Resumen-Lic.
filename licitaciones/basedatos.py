"""Memoria del sistema (SQLite, un solo archivo local, costo cero).

Guarda:
- Cada licitación vista, y si ya fue enviada por mail.
  Se envía "todo lo que todavía no se envió", así una corrida fallida no pierde nada.
- Cada consulta a cada fuente, para detectar fuentes caídas o rediseñadas.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .modelo import Licitacion

ESQUEMA = """
CREATE TABLE IF NOT EXISTS licitaciones (
    uid TEXT PRIMARY KEY,
    fuente TEXT NOT NULL,
    datos TEXT NOT NULL,
    detectada_en TEXT NOT NULL,
    enviada_en TEXT
);
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente TEXT NOT NULL,
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL,          -- 'ok' o 'error'
    visibles INTEGER NOT NULL,     -- licitaciones que mostraba la página
    nuevas INTEGER NOT NULL,
    mensaje TEXT
);
"""


class BaseDatos:
    def __init__(self, ruta: str | Path) -> None:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(ruta)
        self.con.executescript(ESQUEMA)

    def guardar(self, lic: Licitacion, ahora: str) -> bool:
        """Guarda la licitación. Devuelve True si es nueva.

        Si ya existía y todavía no se envió, actualiza sus datos (por si la fuente los corrigió).
        """
        datos = json.dumps(lic.a_dict(), ensure_ascii=False)
        with self.con:
            cur = self.con.execute(
                "INSERT OR IGNORE INTO licitaciones (uid, fuente, datos, detectada_en) VALUES (?, ?, ?, ?)",
                (lic.uid, lic.fuente, datos, ahora),
            )
            if cur.rowcount == 1:
                return True
            self.con.execute(
                "UPDATE licitaciones SET datos = ? WHERE uid = ? AND enviada_en IS NULL",
                (datos, lic.uid),
            )
            return False

    def pendientes(self) -> list[Licitacion]:
        filas = self.con.execute(
            "SELECT datos FROM licitaciones WHERE enviada_en IS NULL ORDER BY fuente, detectada_en"
        ).fetchall()
        return [Licitacion.desde_dict(json.loads(f[0])) for f in filas]

    def marcar_enviadas(self, uids: list[str], ahora: str) -> None:
        with self.con:
            self.con.executemany(
                "UPDATE licitaciones SET enviada_en = ? WHERE uid = ?", [(ahora, u) for u in uids]
            )

    def registrar_consulta(self, fuente: str, ahora: str, estado: str, visibles: int, nuevas: int,
                           mensaje: str = "") -> None:
        with self.con:
            self.con.execute(
                "INSERT INTO consultas (fuente, fecha, estado, visibles, nuevas, mensaje) VALUES (?, ?, ?, ?, ?, ?)",
                (fuente, ahora, estado, visibles, nuevas, mensaje),
            )

    def racha_sin_resultados(self, fuente: str) -> int:
        """Cuántas consultas seguidas (las más recientes) terminaron en error o con 0 visibles."""
        filas = self.con.execute(
            "SELECT estado, visibles FROM consultas WHERE fuente = ? ORDER BY id DESC LIMIT 50", (fuente,)
        ).fetchall()
        racha = 0
        for estado, visibles in filas:
            if estado == "ok" and visibles > 0:
                break
            racha += 1
        return racha
