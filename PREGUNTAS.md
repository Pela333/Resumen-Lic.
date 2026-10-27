# Parámetros y Preferencias del Proyecto: Resumen de Licitaciones

> **Nota:** Este archivo contiene las definiciones del negocio y requerimientos del sistema. 
> Si se modifican los valores o criterios aquí listados, el sistema ajustará su comportamiento según estas pautas.

---

## 1. Perfil de la Empresa y Criterio de Selección

* **Tipo de empresa:** Constructora.
* **Especialidad principal:** Obras viales y obras de arquitectura.
* **Criterio de filtrado:**
  * **NO** utilizar filtros de palabras clave rígidas (evitar descartar licitaciones por diferencias léxicas, ej.: "pavimento" vs "carpeta asfáltica" vs "hormigonado").
  * En portales específicos de obra (Vialidad, Infraestructura, AUBASA, OPISU, etc.), se recolecta **todo** lo publicado, ya que por definición pertenece al rubro.
  * En portales generalistas y boletines (Boletín Oficial PBA, Boletín Oficial Nación), se capturan también llamados a licitación pública de municipios (La Plata, Vicente López, Saladillo, Quilmes, Roque Pérez, Avellaneda, Lanús, Morón, etc.).
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

1. **Filtro de obras vs. servicios:**
   * **Criterio general:** Solo se incluyen **obras** (arquitectura, viales, hidráulicas, etc.).
   * **Excepción para prueba piloto:** Para este primer test se incluye la licitación actual de AUBASA (servicio de monitoreo) para validar la recepción del mail y el diseño del PDF.
2. **Cuenta de envío:**
   * Configurada cuenta Gmail dedicada: `ignaciobordoli44@gmail.com` con contraseña de aplicación de 16 caracteres. Destinatario actual: `ignaciobordoli44@gmail.com`.
3. **Entorno de ejecución programada:**
   * **GitHub Actions** (programado para lunes, miércoles y viernes a las 8:00 AM hora argentina / 11:00 UTC).
   * Persistencia de base de datos (`licitaciones.db`) mediante guardado automático en el repositorio para no repetir envíos entre ejecuciones en la nube.

