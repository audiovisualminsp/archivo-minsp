# -*- coding: utf-8 -*-
"""Mapa ruta -> localidades. Base curada + lo que se deduce del propio archivo."""
import re, collections

# Trazas principales de Córdoba. Editable: sumar renglones cuando haga falta.
BASE = {
 '38':  ['Córdoba','Cosquín','La Falda','Capilla del Monte','Villa Giardino','Huerta Grande',
         'Valle Hermoso','Cruz del Eje','San Marcos Sierras'],
 '20':  ['Córdoba','Villa Carlos Paz','Mina Clavero','Villa Dolores','Nono'],
 '36':  ['Córdoba','Río Cuarto','Berrotarán','Almafuerte','Malvinas Argentinas'],
 '9':   ['Córdoba','Jesús María','Colonia Caroya','Villa del Totoral','Villa María','Bell Ville','Marcos Juárez'],
 '60':  ['Córdoba','Jesús María','Deán Funes','Quilino'],
 '158': ['Villa María','General Deheza','General Cabrera','Río Cuarto','San Francisco'],
 '5':   ['Córdoba','Alta Gracia','Villa General Belgrano','Santa Rosa de Calamuchita',
         'Embalse','Villa Rumipal','Villa del Dique'],
 '28':  ['Villa Carlos Paz','Tanti','Taninga'],
 '34':  ['Villa Carlos Paz','Mina Clavero','Villa Cura Brochero'],
 '6':   ['Río Tercero','Villa Rumipal','Embalse'],
 'E53': ['Córdoba','Río Ceballos','Salsipuedes','Agua de Oro','Unquillo'],
 'E55': ['Córdoba','Villa Allende','La Calera','Mendiolaza'],
}

# Reconoce: ruta 28 · r28 · rp28 · rp 28 · r.p.28 · ruta provincial 28 · rn 38 · au 9 · rp s-228
RUTA_RE = re.compile(
    r'(?i)(?<![a-z0-9])'
    r'(?:r(?:uta)?s?\.?\s*(?:p(?:rov(?:incial)?)?|n(?:ac(?:ional)?)?)?\.?|au(?:tov[ií]a)?)'
    r'\s*n?[°ºo]?\s*[-–.:]?\s*([a-z]?\s*[-–.]?\s*\d{1,3}[-–]?[a-z]?)(?![0-9])')

def normalizar_ruta(s):
    return re.sub(r'[\s.\-–]', '', s).upper()

def extraer_rutas(texto):
    return {normalizar_ruta(m.group(1)) for m in RUTA_RE.finditer(texto or '')}

def construir_mapa(filas):
    """Cruza las rutas mencionadas con las localidades detectadas en cada operativo."""
    mapa = collections.defaultdict(collections.Counter)
    for k, locs in BASE.items():
        for l in locs:
            mapa[normalizar_ruta(k)][l] += 3        # la base pesa más que un hallazgo suelto
    for r in filas:
        rutas = extraer_rutas(r.get('ruta', '') + ' ' + r.get('descripcion', ''))
        for rt in rutas:
            for loc in (r.get('localidades') or '').split('; '):
                if loc: mapa[rt][loc] += 1
    return {k: [l for l, _ in v.most_common(10)] for k, v in mapa.items() if v}
