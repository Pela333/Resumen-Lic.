# Catálogo General de Fuentes de Licitaciones

> Registro maestro de todos los portales de licitaciones a monitorear por el sistema.
> Las fuentes se agrupan por familia tecnológica para maximizar la reutilización de código.

---

## Estado General

| Total Fuentes | Activas (Producción) | En Análisis / Desarrollo | Pendientes |
| :---: | :---: | :---: | :---: |
| **36+** | **13** (AUBASA, Vialidad PBA, AUSA, AUSOL, CONTRAT.AR, BA Obras, PBAC, COMPR.AR, BAC, Minfra PBA, OPISU, Hábitat, COMIREC) | **1** (Corredores Viales) | **22** |

---

## 1. Familia: Concesionarias Viales y Autopistas
*Portales con tablas o listados específicos de infraestructura vial y peajes.*

| Organismo | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **AUBASA** | `https://compras.aubasa.com.ar/` | ✅ **Activo** | HTML directo (`licitaciones/fuentes/aubasa.py`). |
| **AUSOL** (Autopistas del Sol) | `https://www.ausol.com.ar/licitaciones` | ✅ **Activo** | Next.js JSON en HTML (`licitaciones/fuentes/ausol.py`). |
| **AUSA** (Autopistas Urbanas CABA) | `https://www.ausa.com.ar/proveedores/licitaciones` | ✅ **Activo** | API REST interna (`licitaciones/fuentes/ausa.py`). |
| **Corredores Viales S.A.** | `https://corredoresvialessa.com.ar/licitaciones/bienes/publicas` | ⏳ Pendiente | Empresa estatal nacional vial. |

---

## 2. Familia: Plataforma de Compras Electrónicas (ASP.NET)
*Comparten la misma arquitectura base (software de contrataciones públicas con formularios `.aspx`). Todas activas.*

| Organismo / Portal | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **CONTRAT.AR** (Nación Obra) | `https://contratar.gob.ar/ListarAperturaProxima.aspx` | ✅ **Activo** | Obra pública nacional (`licitaciones/fuentes/contratar.py`). Resuelve enlaces pliego ciudadano directo. |
| **BA Obras** (CABA) | `https://buenosairesobras.dguiaf-gcba.gov.ar/ListarAperturaProxima.aspx` | ✅ **Activo** | Obra pública CABA (`licitaciones/fuentes/ba_obras.py`). Sesión BIG-IP ASP.NET gestionada. |
| **PBAC** (PBA Compras) | `https://pbac.cgp.gba.gov.ar/ListarAperturaProxima.aspx` | ✅ **Activo** | Compras PBA (`licitaciones/fuentes/pbac.py`). Filtro de obras y pliego ciudadano directo. |
| **COMPR.AR** (Nación) | `https://comprar.gob.ar/Compras.aspx?qs=W1HXHGHtH10=` | ✅ **Activo** | Contrataciones Nación (`licitaciones/fuentes/comprar.py`). Filtro de infraestructura/obras. |
| **BAC** (Buenos Aires Compras) | `https://www.buenosairescompras.gob.ar/ListarAperturaProxima.aspx` | ✅ **Activo** | Compras CABA (`licitaciones/fuentes/bac.py`). Filtro de mantenimiento edilicio/obras. |


---

## 3. Familia: Portales GBA (Gobierno de la Provincia de Buenos Aires)
*Sitios institucionales provinciales (Drupal CMS / iframes de infraestructura).*

| Organismo | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **Min. Infraestructura PBA** | `https://www.minfra.gba.gob.ar/licitacionesV2/obras` | ✅ **Activo** | Obra pública provincial mayor (`licitaciones/fuentes/minfra.py`). Extrae presupuesto oficial y lugar de apertura. |
| **OPISU - Obras y Bienes** | `https://adquisiciones.opisu.gba.gob.ar/obras` | ✅ **Activo** | Integración Social y Urbana (`licitaciones/fuentes/opisu.py`). Monitorea ambas tablas. |
| **Hábitat PBA** | `https://www.gba.gob.ar/habitat/licitaciones` | ✅ **Activo** | Min. de Hábitat y Desarrollo Urbano (`licitaciones/fuentes/habitat.py`). Detalle de obras y fechas. |
| **COMIREC** | `https://www.gba.gob.ar/comirec/contrataciones_comirec` | ✅ **Activo** | Cuenca del Río Reconquista (`licitaciones/fuentes/comirec.py`). Licitaciones hidráulicas y saneamiento. |
| **Justicia y DDHH PBA** | `https://www.gba.gob.ar/justicia_y_ddhh/licitaciones` | ⏳ Pendiente | Sin llamados activos en la web. |
| **Ambiente PBA (PNUD)** | `https://www.ambiente.gba.gob.ar/contenido/licitaciones_proyecto_pnud_arg22008_0` | ⏳ Pendiente | Sin llamados activos (últimos de 2025). |
| **DGCyE (Escuelas / ABC)**| `https://abc2.abc.gob.ar/area_administrativa` | ⏳ Pendiente | Cifrado legado DH. |
| **Sistemas GBA** | `https://sistemas.gba.gob.ar/consulta/contrataciones/` | ⏳ Pendiente | Redirige a consulta provincial. |


---

## 4. Familia: Single Page Apps (SPA) / APIs Dinámicas
*Cargan datos con JavaScript (Angular/React/Vue). Se exploran para consumir sus APIs JSON internas sin cargar la web completa.*

| Organismo | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **Vialidad PBA** | `http://www.vialidad.gba.gov.ar/apps/angular/licitaciones/#/` | ✅ **Activo** | API JSON directa (`licitaciones/fuentes/vialidad.py`). |
| **ABSA** (Aguas Bonaerenses) | `https://proveedores.aguasbonaerenses.com.ar/#/guest` | ⏳ Pendiente | Portal de proveedores (invitados). |

---

## 5. Familia: Saneamiento, Agua y Puertos
*Grandes entes autárquicos y empresas públicas de servicios y transporte.*

| Organismo | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **AySA** | `https://www.aysa.com.ar/proveedores/licitaciones` | ⏳ Pendiente | Agua y Saneamientos Argentinos S.A. |
| **ACUMAR** | `https://www.acumar.gob.ar/transparencia/compras-y-contrataciones/` | ⏳ Pendiente | Cuenca Matanza Riachuelo. |
| **Puerto La Plata** | `https://puertolaplata.com/servicios-y-negocios/licitaciones-publicadas` | ⏳ Pendiente | Consorcio de Gestión del Puerto. |
| **AGP** (Puertos) | `https://www.agpsau.gob.ar/llamados/82` | ⏳ Pendiente | Administración General de Puertos S.E. |
| **Aeropuertos Argentina** | `https://www.aeropuertosargentina.com/es/sobre-nosotros/licitaciones` | ⏳ Pendiente | Concesionaria aeroportuaria (AA2000). |
| **EANA** | `https://www.eana.com.ar/licitaciones` | ⏳ Pendiente | Empresa Argentina de Navegación Aérea. |

---

## 6. Familia: Organismos Especiales y Financiamiento Internacional

| Organismo | URL Oficial | Estado | Notas Técnicas |
| :--- | :--- | :---: | :--- |
| **FOCEM (Mercosur)** | `https://focem.mercosur.int/es/licitaciones/` | ⏳ Pendiente | Fondo de Convergencia Estructural Mercosur. |
| **PROINGED** | `https://www.proinged.org.ar/licitaciones/` | ⏳ Pendiente | Generación Eléctrica Distribuida. |
| **SEDICI (UNLP)** | `https://sedici.unlp.edu.ar/handle/10915/69217/discover?filtertype=dateIssued&filter_relational_operator=equals&filter=2026` | ⏳ Pendiente | Repositorio DSpace UNLP. |
| **Senado de la Nación** | `https://www.senado.gob.ar/administrativo/Licitaciones` | ⏳ Pendiente | Contrataciones administrativas legislativas. |
| **Ambiente Nación** | `https://www.argentina.gob.ar/ambiente/licitaciones-especiales` | ⏳ Pendiente | Licitaciones especiales y con crédito internacional. |
| **GCABA Histórico** | `https://buenosaires.gob.ar/gcaba_historico/licitaciones-en-curso/licitaciones-publicas-2026` | ⏳ Pendiente | Corporación / listado anual. |

---

## 7. Familia: Boletines Oficiales (Municipales y Generales)
*Fuentes macro donde se publican avisos de licitaciones de municipios del interior y conurbano.*

| Fuente | URL Oficial | Cobertura | Notas |
| :--- | :--- | :--- | :--- |
| **Boletín Oficial PBA** | `https://boletinoficial.gba.gob.ar/` | 135 Municipios bonaerenses + entes provinciales | Sección Municipal y Oficial. |
| **Boletín Oficial CABA** | `https://boletinoficial.buenosaires.gob.ar/` | Ciudad Autónoma de Buenos Aires | Separata y contrataciones. |
| **Boletín Oficial Nación** | `https://www.boletinoficial.gob.ar/` | Nacional y entes federales | 3ª sección (Contrataciones). |
