"""Filtro de pertinencia temática y de monto para empresas constructoras.

Criterio de negocio (PREGUNTAS.md):
- Empresa constructora orientada a:
  * Obras de arquitectura y edificación (hospitales, escuelas, viviendas, galpones,
    remodelaciones y adecuaciones edilicias, cubiertas/techos, etc.).
  * Obras de infraestructura (redes de agua potable, desagües pluviales, cloacas,
    acueductos, gasoductos, tendido eléctrico, subestaciones, puertos, etc.).
  * Obras viales (pavimentación, repavimentación, bacheo, calzadas, puentes vehiculares
    y peatonales, autopistas, autovías, caminos, señalización vial).

Exclusiones taxativas (no son obras):
- Adquisición / provisión / compra de bienes, insumos o repuestos sueltos (indumentaria,
  luminarias/lámparas LED, caños de termofusión, insumos de impermeabilización sin obra,
  repuestos de aire acondicionado, reductores de velocidad plásticos, gases, etc.).
- Servicios menores de mantenimiento o reparación de aparatos puntuales (equipos split,
  grupos electrógenos, luminarias cialíticas de quirófano, instrumental médico, ascensores).
- Servicios de informática, nube y software (desarrollo evolutivo, soporte en la nube,
  plataformas digitales, licencias, fibra óptica pura de telecomunicaciones).
- Pertrechos navales, buques militares o armamento (destructores, sistemas de comando náutico,
  puentes de navegación marina).
- Servicios generales no constructivos (limpieza, seguridad privada, seguros/pólizas, catering).
"""

from __future__ import annotations

import re

# Vocabulario de obras viales, arquitectura, hidráulica, infraestructura y edificaciones
PATRON_OBRA = re.compile(
    r"\b("
    r"obra[s]?(?!\s+(?:social|de\s+t[ií]teres|en\s+(?:el\s+expediente|la\s+solicitud|autos|fojas|el\s+pliego)|agregad[ao]))|"
    r"ley\s*(?:n[°ºo.]*)?\s*(?:13\.?064|6\.?021|130)\b|"
    # Arquitectura / Edificación
    r"construcci[oó]n|construcciones|edificaci[oó]n|edificaciones|arquitectur[a-z]*|"
    r"remodelaci[oó]n|remodelaciones|refacci[oó]n|refacciones|readecuaci[oó]n|readecuaciones|"
    r"adecuaci[oó]n|adecuaciones|puesta\s+en\s+valor|restauraci[oó]n|ampliaci[oó]n|ampliaciones|"
    r"alba[nñ]iler[ií]a|mamposter[ií]a|demolici[oó]n|demoliciones|galp[oó]n|galpones|tinglado[s]?|hangar[a-z]*|"
    r"vivienda[s]?|h[aá]bitat|fachada[s]?|cubierta[s]?|tinglado[s]?|tanque[s]?\s+de\s+agua|tanques?\s+de\s+reserva|"
    r"cielorraso[s]?|techado|"
    r"polideportivo[s]?|gimnasio[s]?|centro[s]?\s+deportivo[s]?|"
    r"montaje\s+de\s+estructura[s]?|montaje\s+estructural|estructura[s]?\s+met[aá]lica[s]?|"
    r"impermeabiliz[a-z]*|filtraci[oó]n|filtraciones|humedad|"
    r"mantenimiento\s+edilicio|reparaci[oó]n\s+edilicia|mantenimiento\s+de\s+edificio[s]?|reparaci[oó]n\s+de\s+edificio[s]?|"
    r"relocalizaci[oó]n\s+de\s+servicios|reforma\s+en\s+internaci[oó]n|"
    # Vialidad / Transporte
    r"vial|viales|paviment[a-z]*|asfalt[a-z]*|hormig[oó]n[a-z]*|bacheo[s]?|calzada[s]?|"
    r"sellado\s+de\s+juntas|sellado\s+de\s+grietas|"
    r"paso[s]?\s+bajo\s+nivel|paso[s]?\s+a\s+nivel|"
    r"puente[s]?\s+(?:vial|peatonal|vehicular|ferroviario|sobre\s+arroyo|sobre\s+r[ií]o)|"
    r"obras?\s+(?:de\s+)?puentes?|construcci[oó]n\s+(?:de\s+)?puentes?|"
    r"autopista[s]?|autov[ií]a[s]?|caminos?\s+rurales?|calzada\s+principal|"
    r"se[nñ]alamiento\s+vial|demarcaci[oó]n\s+(?:vial|horizontal|vertical)|guardarrail[a-z]*|"
    r"cord[oó]n\s+cuneta|bicisenda[s]?|ciclov[ií]a[s]?|"
    # Infraestructura hidráulica, sanitaria y redes
    r"hidr[aá]ulic[a-z]*|desag[uü]e[s]?|sumidero[s]?|pluvial[a-z]*|aliviador[a-z]*|drenaje[s]?|canalizaci[oó]n|cuenca[s]?|"
    r"acueducto[s]?|gasoducto[s]?|cloac[a-z]*|red\s+cloacal|redes\s+cloacales|colector(?:es)?\b|"
    r"red\s+de\s+agua|provisi[oó]n\s+de\s+agua|agua\s+potable|saneamiento|planta\s+depuradora|"
    r"red\s+el[eé]ctrica|sistema\s+el[eé]ctrico|tendido\s+el[eé]ctrico|subestaci[oó]n\s+transformadora|l[ií]nea\s+de\s+alta\s+tensi[oó]n|electrificaci[oó]n|"
    r"alumbrado\s+p[uú]blico|reconversi[oó]n\s+lum[ií]nica|parque\s+lum[ií]nico|"
    # Instalaciones de obra
    r"instalaci[oó]n\s+(?:el[eé]ctrica|sanitaria|de\s+gas|termomec[aá]nica|contra\s+incendio)|"
    r"adecuaci[oó]n\s+el[eé]ctrica|"
    # Portuario y aeroportuario
    r"portuari[a-z]*|muelle[s]?|espig[oó]n[a-z]*|dragado[s]?|d[aá]rsena[s]?|pista\s+de\s+aterrizaje|calle\s+de\s+rodaje"
    r")\b",
    re.IGNORECASE,
)

# Exclusiones específicas (compras de insumos, servicios no constructivos, informática, equipamiento, salud)
PATRON_EXCLUSION = re.compile(
    r"\b("
    # 0. Salud / Hospitales / Medicina (descartados por directiva comercial)
    r"ministerio\s+de\s+salud|"
    r"adquisici[oó]n\s+de\s+medicamentos|medicamentos?\b|farmacia\b|f[aá]rmacos?|"
    r"insumos?\s+para\s+laboratorio|bacterias?\s+y\s+levaduras|hemograma|determinaciones?\s+de\s+gases|"
    r"estreptoquinasa|material\s+de\s+esterilizaci[oó]n|residuos\s+patog[eé]nicos|"
    # 1. Compras / Suministros / Insumos de bienes (corralón, ferretería, librería, limpieza, vehículos, etc.)
    r"adquisici[oó]n\s+de\s+(?:materiales|insumos|elementos|repuestos|herramientas|ferreter[ií]a|limpieza|librer[ií]a|v[ií]veres|alimentos|frutas|verduras|insecticidas|seguridad|bienes|gases|medicamentos|descartables|trofeos|mobiliario|resmas|papel|camioneta|pick[\s\-]?up|veh[ií]culos)|"
    r"compra\s+de\s+(?:materiales|insumos|elementos|repuestos|herramientas|ferreter[ií]a|limpieza|librer[ií]a|v[ií]veres|alimentos|frutas|verduras|insecticidas|seguridad|bienes|gases|medicamentos|descartables|trofeos|mobiliario|resmas|papel|camioneta|pick[\s\-]?up|veh[ií]culos)|"
    r"adquirir\s+(?:materiales|insumos|elementos|repuestos|herramientas|ferreter[ií]a|limpieza|librer[ií]a|v[ií]veres|alimentos|frutas|verduras|insecticidas|seguridad|bienes|gases|medicamentos|descartables|trofeos|mobiliario|resmas|papel|camioneta|pick[\s\-]?up|veh[ií]culos)|"
    r"adquisici[oó]n\s+de\s+materiales\s+de\s+construcci[oó]n|compra\s+de\s+materiales\s+de\s+construcci[oó]n|"
    r"provisi[oó]n\s+de\s+veh[ií]culos|adquisici[oó]n\s+de\s+veh[ií]culos|camioneta\b|pick[\s\-]?up|"
    r"trofeos?\b|art[ií]culos?\s+para\s+trofeos|"
    r"adquisici[oó]n\s+de\s+indumentaria|indumentaria\s+(?:de|para|laboral|del\s+personal)|uniforme[s]?\b|"
    r"adquisici[oó]n\s+(?:de\s+)?luminarias?|luminarias?\s+led|l[aá]mparas?\s+led|tubos?\s+led|"
    r"provisi[oó]n\s+de\s+luminaria|compra\s+de\s+luminaria|"
    r"reductores?\s+de\s+velocidad|"
    r"insumos?\s+para\s+impermeabilizar|insumos?\s+para\s+techo|"
    r"elementos?\s+de\s+termofusi[oó]n|termofusi[oó]n\s+para\s+calefacci[oó]n|"
    r"rep(?:uestos)?\s+y\s+acc(?:esorios)?|accesorios?\s+de\s+aires?|repuestos?\s+de\s+aire|"
    r"adquisici[oó]n\s+(?:de\s+)?(?:\d+[\(\)\w\s]{0,20})?equipos?\s+de\s+aire|"
    r"adquisici[oó]n\s+de\s+(?:un\s+)?equipos?|"
    r"adquisici[oó]n\s+de\s+gases|prueba\s+hidr[aá]ulica\s+(?:con\s+destino|de\s+cilindros|de\s+tubos|de\s+garrafas)|"
    r"adquisici[oó]n\s+elementos\s+de\s+hidr[aá]ulica|gr[uú]as?\s+palfinger|gr[uú]as?|bips\b|"
    r"papel\s+obra\b|"
    # 2. Servicios menores / mantenimiento de aparatos / oficinas
    r"fotocopiadoras?\b|alquiler\s+de\s+fotocopiadoras|"
    r"servicio\s+de\s+riego|alquiler\s+de\s+servicio\s+de\s+riego|"
    r"concesi[oó]n\s+de\s+uso\s+precario|explotaci[oó]n\s+de\s+la\s+cantina|"
    r"luminarias?\s+(?:cial[ií]ticas?|scial[ií]ticas?)|l[aá]mparas?\s+(?:cial[ií]ticas?|scial[ií]ticas?)|"
    r"reparaci[oó]n\s+(?:de\s+)?luminaria\s+(?:cial[ií]tica|scial[ií]tica)|"
    r"servicio\s+(?:anual\s+)?(?:de\s+)?mantenimiento\s+(?:preventivo|correctivo|integral)?\s+(?:y\s+(?:preventivo|correctivo)\s+)?de\s+(?:los\s+)?equipos\s+de\s+aire|"
    r"soluci[oó]n\s+aire\s+acondicionado|mantenimiento\s+de\s+aires?\s+acondicionados?|servicio\s+y\s+mantenimiento\s+de\s+aires?|"
    r"tipo\s+split\s+de\s+\d+|provisi[oó]n\s+y\s+colocaci[oó]n\s+aires?\s+acondicionados?|"
    r"(?:servicio\s+de\s+)?mantenimiento\s+(?:integral|correctivo\s+y\s+preventivo|preventivo\s+y\s+correctivo|preventivo|correctivo)?\s+(?:de\s+)?grupo[s]?\s+electr[oó]geno[s]?|"
    r"recarga\s+de\s+matafuegos|service\s+de\s+ascensores|"
    r"tom[oó]grafo|resonador|aparatos?\s+m[eé]dicos?|equipamiento\s+de\s+cocina|"
    # 3. Informática / Nube / Software / Monitoreo
    r"infraestructura\s+(?:en\s+la\s+nube|cloud|tecnol[oó]gica|inform[aá]tica|digital)|"
    r"infraestructura\s+de\s+(?:firewall|redes\s+inform[aá]ticas)|"
    r"en\s+la\s+nube|cloud|desarrollo\s+evolutivo|soporte,\s*mantenimiento\s+e\s+infraestructura\s+en\s+la\s+nube|"
    r"plataforma\s+agp|plataforma\s+web|licencias?\s+de\s+software|sistemas?\s+inform[aá]ticos?|"
    r"tendido\s+de\s+fibra\s+[oó]ptica|fibra\s+[oó]ptica|conectividad\s+web|virtualizaci[oó]n|"
    r"sap\s+successfactors|"
    r"sistema\s+de\s+monitoreo|c[aá]maras\s+de\s+seguridad|videovigilancia|monitoreo\s+por\s+video|"
    # 4. Naval militar / buques
    r"puente\s+de\s+navegaci[oó]n|destructor\s+a\.?r\.?a|a\.?r\.?a\.?\s*[\"']?sarand[ií]|"
    r"sistema\s+hidr[aá]ulico\s+del\s+destructor|buque\s+militar|corbeta|fragata|"
    # 5. Servicios generales no constructivos / Recursos humanos
    r"servicio\s+de\s+limpieza|servicio\s+de\s+seguridad|servicio\s+de\s+vigilancia|"
    r"servicio\s+de\s+difusi[oó]n|transmisiones\s+de\s+automovilismo|"
    r"seguro[s]?\s+contra|responsabilidad\s+civil\s+para\s+directores|p[oó]liza\s+de\s+seguro|"
    r"servicio\s+de\s+catering|alimentos|medicamentos|pr[oó]tesis|"
    r"recolecci[oó]n\s+de\s+residuos|concesi[oó]n\s+de\s+v[ií]as\s+e\s+inmuebles|"
    r"servicios?\s+de\s+consultor[ií]a\s+de\s+la\s+obra|prefactibilidad\s+t[eé]cnica\s+e\s+ingenier[ií]a\s+conceptual|"
    r"elaboraci[oó]n\s+de\s+un\s+proyecto\s+de\s+instalaci[oó]n|"
    r"concurso\s+p[uú]blico|cobertura\s+de\s+(?:\d+\s+)?cargo|cargo\s+de\s+m[eé]dico"
    r")\b",
    re.IGNORECASE,
)


def es_de_obra_o_arquitectura(texto: str, organismo: str = "") -> bool:
    """Evalúa si el objeto de la licitación corresponde a obras de construcción, arquitectura o vialidad."""
    if not texto:
        return False
    texto_evaluar = f"{organismo} {texto}" if organismo else texto

    # Regla expresa: descartar licitaciones del Ministerio de Salud o centros de salud hospitalarios
    if organismo and re.search(r"\b(?:ministerio\s+de\s+salud|hospital\b|higa\b|hiea\b|hza\b|hma\b)", organismo, re.IGNORECASE):
        return False

    if PATRON_EXCLUSION.search(texto_evaluar):
        return False
    return bool(PATRON_OBRA.search(texto_evaluar))


def parsear_monto_pesos(texto: str) -> float | None:
    """Extrae el valor numérico en pesos (ARS) de una cadena de presupuesto o monto.

    Admite formatos comunes argentinos:
      '$ 114.778.350,00' -> 114778350.0
      '$2.504.026.390,89' -> 2504026390.89
      '$ 7638061962,000000' -> 7638061962.0
      'USD 930.000,00' -> 930000.0 * 1350 (aprox oficial/libre para referencia)
    """
    if not texto or "no informado" in texto.lower():
        return None

    # Presupuesto en dólares
    es_usd = bool(re.search(r"\b(?:usd|u\$s|d[oó]lares)\b", texto, re.IGNORECASE))

    # Buscar secuencia monetaria
    m = re.search(r"[\$]?\s*([\d]{1,3}(?:\.[\d]{3})+(?:,[\d]+)?|[\d]+(?:,[\d]+)?)", texto)
    if not m:
        return None

    num_str = m.group(1).replace(".", "").replace(",", ".")
    try:
        val = float(num_str)
        if es_usd:
            # Multiplicador orientativo de USD a ARS para comparar umbrales
            val *= 1350.0
        return val
    except ValueError:
        return None


def cumple_filtro_monto(
    presupuesto_str: str,
    monto_minimo_pesos: float = 0.0,
    descartar_si_no_informado: bool = False,
) -> bool:
    """Valida si la licitación cumple con la política de montos mínimos configurada."""
    if monto_minimo_pesos <= 0:
        return True

    monto = parsear_monto_pesos(presupuesto_str)
    if monto is None:
        # No se publicó el presupuesto en la web
        return not descartar_si_no_informado

    return monto >= monto_minimo_pesos
