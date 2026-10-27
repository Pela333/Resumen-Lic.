# Resumen automático de licitaciones

Revisa las páginas de licitaciones de distintos organismos, detecta las nuevas y envía
un resumen por mail (cuerpo legible en el celular + PDF adjunto).

- **Preferencias de negocio** (qué se busca, para quién, cuándo): [PREGUNTAS.md](PREGUNTAS.md)
- **Configuración técnica** (fuentes activas, alertas): [config.toml](config.toml)
- **Claves y contraseñas**: archivo `.env` (copiar desde [.env.example](.env.example)). Nunca se comparte.

## Cómo se usa

Primera vez (instala lo necesario en una carpeta aislada `.venv`):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Generar el reporte **sin enviar mail** (para probar). Queda en la carpeta `salida/`:

```powershell
.\.venv\Scripts\python.exe -m licitaciones --sin-enviar
```

Corrida real (envía el mail si `.env` está completo):

```powershell
.\.venv\Scripts\python.exe -m licitaciones
```

## Cómo funciona

1. **Recolectar**: cada organismo tiene su propio archivo en `licitaciones/fuentes/`.
   Si uno falla, los demás siguen.
2. **Recordar**: `datos/licitaciones.db` guarda lo ya visto y lo ya enviado.
   Se envía todo lo que todavía no se mandó, así un día con fallas no pierde nada.
3. **Armar el resumen**: HTML para el cuerpo del mail y PDF adjunto.
4. **Enviar**: por Gmail. Solo si el envío sale bien se marcan las licitaciones como enviadas.
5. **Avisar fallas**: cada mail incluye el estado de cada fuente. Si una falla, o muestra 0
   licitaciones varias veces seguidas, el mail lo dice en rojo.

## Fuentes

| Fuente | Estado | Método |
|---|---|---|
| AUBASA | Funcionando (piloto) | HTML directo |
| Vialidad PBA, OPISU, Infraestructura PBA, BA Obras, GCABA, Boletín Oficial, SEDICI | Pendientes | A definir tras inspeccionar cada una |

## Agregar una fuente nueva

1. Crear `licitaciones/fuentes/<nombre>.py` con una clase que herede de `Fuente` (ver `aubasa.py`).
2. Importarla en `licitaciones/fuentes/__init__.py`.
3. Agregar su clave en `config.toml > [fuentes] activas`.
