# Parámetros y Preferencias del Proyecto: Resumen de Licitaciones

> **Nota:** Este archivo contiene las definiciones del negocio y requerimientos del sistema. 
> Si se modifican los valores o criterios aquí listados, el sistema ajustará su comportamiento según estas pautas.

---

## 1. Perfil de la Empresa y Criterio de Selección

* **Tipo de empresa:** Constructora.
* **Especialidad principal:** Obras viales y obras de arquitectura.
* **Criterio de vigencia de fechas:**
  * **Solo licitaciones abiertas / vigentes:** Se descartan automáticamente llamados cuya fecha de apertura ya haya pasado (`fecha_apertura < hoy`) o figuren como adjudicadas/finalizadas, aunque el organismo las siga mostrando en su sitio.
* **Criterio de filtrado temático:**
  * **Empresa constructora:** Obras de arquitectura, infraestructura (hidráulica, cloacal, agua, eléctrica de media/alta tensión, portuaria) y viales de cualquier tipo.
  * **Exclusiones automáticas:**
    - Compras y adquisiciones de bienes, suministros e insumos sueltos (indumentaria/uniformes, luminarias/lámparas LED, caños/termofusión, insumos de impermeabilización, repuestos de aire acondicionado, reductores de velocidad plásticos, gases, etc.).
    - Servicios menores de mantenimiento de equipos o aparatos puntuales (equipos de aire acondicionado, grupos electrógenos, luminarias cialíticas de quirófano, instrumental médico, ascensores).
    - Tecnología, software y servicios en la nube (desarrollo evolutivo, soporte en la nube, plataformas web, fibra óptica pura de datos).
    - Pertrechos navales y equipamiento militar bélico (destructores, buques, puentes de navegación, sistemas hidráulicos navales).
    - Servicios generales no constructivos (limpieza, seguridad privada, seguros/pólizas, catering).
  * **Portales y boletines:** Se monitorean los 34 portales y boletines oficiales (Nación, CABA, PBA y municipios) aplicando este filtrado tanto en origen como de manera centralizada.
  * **Filtro de montos mínimos:** Configurable en `config.toml` (`[filtros].presupuesto_minimo_pesos`). Permite establecer un umbral de presupuesto oficial mínimo para descartar obras pequeñas.
  * Catálogo completo de enlaces y estado de desarrollo: ver archivo [FUENTES.md](FUENTES.md).

---

## 2. Campos Requeridos en el Resumen (PDF y Mail)

Para cada licitación detectada, el sistema intentará recopilar los siguientes datos:

1. **Organismo Emisor** (Ej.: Dirección de Vialidad PBA, AUBASA, etc.)
2. **Número de Licitación / Expediente**
3. **Objeto / Descripción de la Obra**
4. **Presupuesto Oficial** (Monto en ARS o USD)
5. **Fecha y Hora Límite de Presentación de Ofertas**
6. **Fecha, Hora y Lugar del Acto de Apertura de Sobres**
7. **Valor del Pliego** (Monto o si es "Sin Costo")
8. **Enlace Directo** a la publicación oficial / pliego digital

---

## 3. Alcance de la Extracción

* **Fase Actual (MVP - $0.00):** La información se extrae **únicamente del contenido visible en las páginas web** (pantallas, tablas, fichas de detalle y datos estructurados).
* **Fase Futura (Escalamiento):** Descarga automática de pliegos adjuntos (archivos PDF) y lectura profunda mediante OCR / IA para buscar presupuestos o plazos que no figuren en la carátula web.

---

## 4. Destinatarios y Canales de Envío

* **Destinatario Principal:** Usuario (correo personal / cuenta designada).
* **Canal Principal:** Correo electrónico con:
  * Cuerpo del mail en HTML visual y ejecutivo (lectura rápida en smartphone).
  * Archivo PDF adjunto con el detalle consolidado listo para archivar/imprimir.
* **Alertas por Montos Extraordinarios / Canales Secundarios:** Desactivadas por el momento. (Preparado para incorporar Telegram / WhatsApp y alertas de presupuestos altos a futuro).

---

## 5. Frecuencia y Horario de Envío

* **Días de Envío:** Lunes, Miércoles y Viernes.
* **Horario de Entrega:** 8:00 AM (Hora Oficial de la República Argentina, UTC-3).
* **Criterio de Novedades:** Control de duplicados por identificador único (ID/Expediente). Se reporta todo lo nuevo publicado desde el último envío exitoso.

---

## 6. Estado de Presupuesto y Roadmap Tecnológico

* **Presupuesto Actual:** **$0.00 USD**.
* **Arquitectura de Fase 1 (Costo Cero):**
  * Extracción: Python con librerías estándar / de código abierto.
  * Clasificación / Ordenamiento IA: Capa gratuita de Google AI Studio (Gemini Flash). Límites de uso gratuito **a verificar** en la página oficial antes de usarla; todavía no hace falta para el piloto.
  * Ejecución programada: Tarea programada local (Windows Task Scheduler) o GitHub Actions Free.
  * Envío de mail: Servidor SMTP gratuito (cuenta de Gmail dedicada con contraseña de aplicación).
* **Arquitectura de Fase 2 (A financiar tras validación exitosa):**
  * Migración a servidor VPS propio en Argentina/Latinoamérica (para evitar bloqueos de IP).
  * Conexión a APIs pagas de IA (Anthropic Claude / OpenAI / Gemini Paid) para procesar pliegos PDF pesados.
  * Incorporación de proxies residenciales en caso de portales con bloqueos anti-bot avanzados.
  * Suma de más fuentes provinciales, nacionales (Compr.AR, Contrat.AR) y municipales.

---

## 7. Decisiones del Usuario y Configuración

1. **Filtro de obras vs. compras y servicios:**
   * **Criterio estricto:** Solo se incluyen **obras** (arquitectura, viales, hidráulicas, sanitarias, eléctricas de envergadura, etc.).
   * Se descartan compras de insumos, servicios de mantenimiento de equipamiento puntual, software/nube y equipamiento naval.
   * Filtro de monto mínimo configurable en `config.toml` (`presupuesto_minimo_pesos`).
2. **Cuenta de envío:**
   * Configurada cuenta Gmail dedicada: `ignaciobordoli44@gmail.com` con contraseña de aplicación de 16 caracteres. Destinatarios: `ignaciobordoli44@gmail.com` y `gremiro.pf@gmail.com`.

3. **Entorno de ejecución programada:**
   * **GitHub Actions** (programado para lunes, miércoles y viernes a las 8:00 AM hora argentina / 11:00 UTC).
   * Persistencia de base de datos (`licitaciones.db`) mediante guardado automático en el repositorio para no repetir envíos entre ejecuciones en la nube.

