# -*- coding: utf-8 -*-
"""
Actualiza el indice del archivo audiovisual del MinSP Cordoba.

Que hace:
  1. Pide a MEGAcmd el arbol de carpetas y la lista de links publicos.
  2. Arma el indice de operativos (fecha, area, localidades, materiales, link).
  3. Escribe indice.json, indice.csv y buscador-archivo.html en la carpeta 'salida'.

Requisitos: Python 3.9+ y MEGAcmd instalado con la sesion ya iniciada.
Uso:  python actualizar_indice.py
"""
import os, re, sys, csv, json, subprocess, unicodedata, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas_map import construir_mapa
from funcionarios import FUNCIONARIOS, ALIAS
import publicar as pub
import planilla as pla

AQUI    = Path(__file__).resolve().parent
SALIDA  = AQUI / 'salida'
PLANTIL = AQUI / 'plantilla'
ANIOS_OK = {'2024', '2025', '2026'}          # <-- editar cuando cambie el rango
MEGA_DIR = Path(os.environ.get('LOCALAPPDATA', '')) / 'MEGAcmd'

def mega(comando, *args):
    """Ejecuta un comando de MEGAcmd y devuelve su salida como texto.

    Funciona igual en Windows (MEGAcmd instalado en AppData) y en Linux,
    donde los comandos mega-* quedan en el PATH.
    """
    import shutil
    orden = None
    if MEGA_DIR.exists():                       # Windows
        for ext in ('.bat', '.exe'):
            cand = MEGA_DIR / f'mega-{comando}{ext}'
            if cand.exists():
                orden = str(cand)
                break
    if orden is None:                           # Linux / PATH
        orden = shutil.which(f'mega-{comando}')
    if orden is None:
        sys.exit(f'No se encontro mega-{comando} (ni en {MEGA_DIR} ni en el PATH)')
    r = subprocess.run([orden, *args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')

SEP = r'[-_./\s]*'
FECHA_PATS = [
    (re.compile(r'^\s*(\d{4})' + SEP + r'(\d{1,2})' + SEP + r'(\d{1,2})(?!\d)'), 'ymd'),
    (re.compile(r'^\s*(\d{1,2})[-_./\s]+(\d{1,2})[-_./\s]+(\d{2,4})(?!\d)'), 'dmy'),
]
FECHA_LIBRE = re.compile(r'(?<!\d)(\d{1,2})[-_./](\d{1,2})[-_./](\d{4})(?!\d)')
MAT = re.compile(r'(?i)^\s*(fotos?|v[ií]deos?|dron[e]?s?|celu(lar)?|raw|crudos?|editad[ao]s?|selecc?ionad[ao]s?|sony|osmo|gopro|c[aá]mara|testimonios?|notas?|placas?|audios?|360|dng|horizontales?|verticales?|reels?|inserts?|edit|nueva carpeta|varios)\b')

def norm(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower().strip()

def _armar(y, mo, d):
    if y < 100: y += 2000
    if mo > 12 and d <= 12: mo, d = d, mo        # tolera AAAA DD MM
    if not (2010 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31): return None
    return f"{y:04d}-{mo:02d}-{d:02d}"

def parse_fecha(seg):
    for pat, kind in FECHA_PATS:
        m = pat.match(seg)
        if not m: continue
        if kind == 'ymd':
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        f = _armar(y, mo, d)
        if f: return f, seg[m.end():].strip(' .-_')
    m = FECHA_LIBRE.search(seg)                  # fecha al final del nombre
    if m:
        f = _armar(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if f: return f, (seg[:m.start()] + seg[m.end():]).strip(' .-_')
    return None, seg

def es_material(s):
    return bool(MAT.match(s))

from localidades import LOCALIDADES

# Lugares que no son localidades pero permiten ubicar el material: avenidas, diques,
# cerros, barrios. Se traducen a la localidad que les corresponde.
REFERENCIAS = {
 'Bodereau':        'Villa Allende',
 'Rancagua':        'Córdoba',
 'Impira':          'Córdoba',
 'Madre Sacramento':'Córdoba',
 'Cerro Blanco':    'Tanti',
 'Dique La Viña':   'Villa Dolores',
 'La Viña':         'Villa Dolores',
}

# Cómo se nombra a cada localidad en la práctica, además de su nombre completo.
VARIANTES = {
 'Cordoba Capital':'Córdoba',
 'Ciudad de Cordoba':'Córdoba',
 'Carlos Paz':      'Villa Carlos Paz',
 'VCP':             'Villa Carlos Paz',
 'Dean Funes':      'Deán Funes',
 'Cura Brochero':   'Villa Cura Brochero',
 'Brochero':        'Villa Cura Brochero',
 'General Belgrano':'Villa General Belgrano',
 'VGB':             'Villa General Belgrano',
 'Santa Rosa':      'Santa Rosa de Calamuchita',
 'Mina Clavero':    'Mina Clavero',
 'Jesus Maria':     'Jesús María',
 'Rio Ceballos':    'Río Ceballos',
 'Alta Gracia':     'Alta Gracia',
 'La Calera':       'La Calera',
 'Villa del Dique': 'Villa del Dique',
}
_EXTRA = {}
for _alias, _dest in list(REFERENCIAS.items()) + list(VARIANTES.items()):
    if _dest in LOCALIDADES:
        _EXTRA[_alias] = (_dest, LOCALIDADES[_dest])

LOC_NORM = sorted(
    [(norm(k), k, v) for k, v in LOCALIDADES.items()] +
    [(norm(a), d, dep) for a, (d, dep) in _EXTRA.items()],
    key=lambda x: -len(x[0]))
ABREV = {'cde':'Cruz del Eje','vcp':'Villa Carlos Paz','rc':'Río Cuarto',
         'vgb':'Villa General Belgrano','sfco':'San Francisco','au':'Autovía',
         'rp':'Ruta Provincial','rn':'Ruta Nacional'}

def detectar_localidades(texto):
    t = norm(texto); found = []
    for nk, orig, depto in LOC_NORM:
        if re.search(r'(?<![a-z0-9])' + re.escape(nk) + r'(?![a-z0-9])', t):
            if not any(nk in norm(f[0]) and nk != norm(f[0]) for f in found):
                found.append((orig, depto))
    for ab, full in ABREV.items():
        if full in LOCALIDADES and re.search(r'(?<![a-z0-9])'+ab+r'(?![a-z0-9])', t):
            if not any(f[0] == full for f in found):
                found.append((full, LOCALIDADES[full]))
    return found

# ---------------------------------------------------------------- construccion
GENERICO = re.compile(r'(?i)^(obras?|reuniones?|actos?|eventos?|secretar|campa|fotos \d{4}|\d{4}$|sub ?secretar|direcci|junio a diciembre)')
LINK_PAT = re.compile(r'^(.*?) \((?:folder|[\d.,]+ [KMGT]?B), shared as exported permanent (?:folder|file) link: (https://mega\.nz/\S+)\)\s*$')

def en_rango(ruta):
    p = [s for s in ruta.split('/') if s]
    if not p: return False
    if p[0].startswith('FOTOS'):
        return p[0].replace('FOTOS', '').strip() in ANIOS_OK
    m = re.match(r'^(\d{4})', p[0])
    return bool(m and m.group(1) in ANIOS_OK)

def clave(s):
    return re.sub(r'\s+', ' ', s).strip().lower()

def construir(rutas, links):
    links_n = {clave(a): b for a, b in links.items()}
    ops = {}
    for ruta in rutas:
        segs = [s for s in ruta.split('/') if s]
        if not segs: continue
        idx = None
        for n, s in enumerate(segs):
            if parse_fecha(s)[0]: idx = n; break
        if idx is None:
            for n in range(1, len(segs)):
                if not es_material(segs[n]) and not GENERICO.match(segs[n]): idx = n; break
        if idx is None: continue

        k = '/' + '/'.join(segs[:idx + 1])
        if k not in ops:
            fecha, desc = parse_fecha(segs[idx])
            anio = segs[0].replace('FOTOS', '').strip() if segs[0].startswith('FOTOS') else ''
            if fecha:
                if anio.isdigit() and fecha[:4] != anio:
                    fecha = anio + fecha[4:]          # corrige typos de año
                anio = fecha[:4]
            ops[k] = {'fecha': fecha or '', 'anio': anio,
                      'descripcion': (desc or segs[idx]).strip(),
                      'area': segs[1] if len(segs) > 2 and segs[0].startswith('FOTOS') else '',
                      'jerarquia': ' > '.join(segs[1:idx]) if idx > 1 else '',
                      'ruta': k, 'subobras': set(), 'materiales': set(), 'texto': set(),
                      'link': links.get(k) or links_n.get(clave(k), '')}
        ops[k]['texto'].add(' '.join(segs))
        for s in segs[idx + 1:]:
            if es_material(s): ops[k]['materiales'].add(s.strip())
            elif not GENERICO.match(s): ops[k]['subobras'].add(s.strip())

    filas = []
    for o in sorted(ops.values(), key=lambda x: x['fecha'] or '0000-00-00', reverse=True):
        loc = detectar_localidades(' | '.join(o['texto']))
        filas.append({'fecha': o['fecha'], 'anio': o['anio'], 'descripcion': o['descripcion'],
                      'area': o['area'], 'jerarquia': o['jerarquia'],
                      'localidades': '; '.join(sorted({l[0] for l in loc})),
                      'departamentos': '; '.join(sorted({l[1] for l in loc})),
                      'subobras': '; '.join(sorted(o['subobras'])[:12]),
                      'materiales': '; '.join(sorted(o['materiales'])[:12]),
                      'ruta': o['ruta'], 'link': o['link'],
                      'nombre_planilla': '', 'area_planilla': '',
                      'link_mega_alt': '', 'link_nas': '', 'link_drive': '',
                      'publicaciones': ''})
    return filas

# ------------------------------------------------------------------------ main
def main():
    SALIDA.mkdir(exist_ok=True)
    hoy = datetime.date.today().isoformat()
    print(f'[{hoy}] Actualizando indice...')

    print('  1/7  Leyendo arbol de carpetas desde MEGA...')
    # Se consulta rama por rama en vez de toda la cuenta: con 9 TB de metadata,
    # pedir '/' entero tarda muchísimo más de lo necesario.
    rutas = []
    for anio in sorted(ANIOS_OK):
        rama = f'/FOTOS {anio}'
        salida = mega('find', rama, '--type=d')
        encontradas = [l.strip() for l in salida.splitlines() if l.startswith('/')]
        if encontradas:
            print(f'        {rama}: {len(encontradas)}')
        rutas.extend(encontradas)
    # Carpetas sueltas en la raíz que empiezan con un año del rango
    for l in mega('find', '/', '--type=d', '--depth=1').splitlines():
        l = l.strip()
        if l.startswith('/') and en_rango(l) and not l.startswith('/FOTOS'):
            rutas.append(l)
    rutas = list(dict.fromkeys(rutas))
    if not rutas:
        sys.exit('  ERROR: MEGAcmd no devolvio carpetas. Verificar que la sesion este iniciada (mega-whoami).')
    print(f'        {len(rutas)} rutas en rango {sorted(ANIOS_OK)}')

    print('  2/7  Leyendo links publicos...')
    links = {}
    for l in mega('export', '/').splitlines():
        m = LINK_PAT.match(l.strip())
        if m: links[m.group(1)] = m.group(2)
    print(f'        {len(links)} links encontrados')

    print('  3/7  Construyendo indice...')
    filas = construir(rutas, links)
    con_link = sum(1 for f in filas if f['link'])
    con_fecha = sum(1 for f in filas if f['fecha'])
    print(f'        {len(filas)} operativos | {con_fecha} con fecha | {con_link} con link')

    (SALIDA / 'indice.json').write_text(
        json.dumps(filas, ensure_ascii=False), encoding='utf-8')
    with open(SALIDA / 'indice.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)

    print('  4/7  Cruzando con la planilla de coberturas...')
    cfg = pub.leer_config(AQUI / 'config.txt')
    pla.descargar(cfg.get('sheet_id'), AQUI / 'planilla.xlsx')
    datos_pla = pla.leer(AQUI / 'planilla.xlsx')
    if datos_pla:
        n = pla.enriquecer(filas, datos_pla)
        # el nombre de la planilla suele traer localidades que el de la carpeta no tiene
        recuperadas = 0
        for r in filas:
            if r['nombre_planilla'] and not r['localidades']:
                loc = detectar_localidades(r['nombre_planilla'])
                if loc:
                    r['localidades']   = '; '.join(sorted({l[0] for l in loc}))
                    r['departamentos'] = '; '.join(sorted({l[1] for l in loc}))
                    recuperadas += 1
        print(f'        {n} operativos enriquecidos | {recuperadas} localidades recuperadas')
    else:
        print('        (sin planilla.xlsx en la carpeta: se omite este paso)')

    print('  5/7  Generando extras (rutas, funcionarios, alias)...')
    extras = {'rutas': construir_mapa(filas), 'funcionarios': FUNCIONARIOS, 'alias': ALIAS}
    (SALIDA / 'extras.json').write_text(
        json.dumps(extras, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'        {len(extras["rutas"])} rutas mapeadas')

    print('  6/7  Generando buscadores HTML...')
    slim = [{'f': r['fecha'], 'd': r['descripcion'], 'a': r['area'], 'j': r['jerarquia'],
             'l': r['localidades'], 'p': r['departamentos'], 's': r['subobras'],
             'm': r['materiales'], 'r': r['ruta'], 'k': r['link'],
             'n': r.get('nombre_planilla', ''),
             'x': r.get('link_mega_alt', ''), 'u': r.get('link_nas', ''),
             'v': r.get('link_drive', ''), 'w': r.get('publicaciones', '')}
            for r in filas]
    (SALIDA / 'indice-web.json').write_text(
        json.dumps(slim, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    datos_js = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    extras_js = json.dumps(extras, ensure_ascii=False, separators=(',', ':'))
    generados = []
    for nombre, salida in (('', 'buscador-archivo.html'), ('chat_', 'buscador-chat.html')):
        h, t = PLANTIL / f'{nombre}head.html', PLANTIL / f'{nombre}tail.html'
        if not (h.exists() and t.exists()):
            continue
        html = h.read_text(encoding='utf-8') + datos_js + \
               t.read_text(encoding='utf-8').replace('EXTRAS_AQUI', extras_js)
        (SALIDA / salida).write_text(html, encoding='utf-8')
        generados.append(salida)
        print(f'        {salida}')
    if not generados:
        print('        (sin plantillas: solo se generaron los JSON y el CSV)')

    print('  7/7  Publicando en GitHub...')
    pub.publicar([SALIDA / 'indice-web.json', SALIDA / 'extras.json'] +
                 [SALIDA / g for g in generados], AQUI / 'config.txt')

    print(f'\nListo. Archivos en: {SALIDA}')

if __name__ == '__main__':
    main()
