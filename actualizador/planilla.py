# -*- coding: utf-8 -*-
"""Lee la planilla de coberturas y la cruza con el índice por el link de MEGA.

La planilla es el archivo .xlsx exportado de Google Sheets. Se espera que esté
en esta misma carpeta. Si no está, el índice se genera igual, sin enriquecer.
"""
import re, urllib.request, urllib.error
from pathlib import Path

# Descarga el libro entero (todas las hojas) desde Google Sheets.
# Requiere que el documento sea accesible por link.
URL_EXPORT = 'https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx'

def descargar(sheet_id, destino):
    """Baja la planilla desde Google Sheets. Devuelve True si se actualizó."""
    if not sheet_id:
        return False
    destino = Path(destino)
    try:
        req = urllib.request.Request(URL_EXPORT.format(id=sheet_id))
        req.add_header('User-Agent', 'indice-archivo-minsp')
        with urllib.request.urlopen(req, timeout=120) as r:
            datos = r.read()
        # Un xlsx siempre arranca con PK; si vino HTML, el documento no es público
        if not datos.startswith(b'PK'):
            print('        (Google devolvio una pagina en vez del archivo: '
                  'revisar que la planilla sea accesible por link)')
            return False
        destino.write_bytes(datos)
        print(f'        planilla descargada de Google Sheets ({len(datos)//1024} KB)')
        return True
    except urllib.error.HTTPError as e:
        print(f'        (no se pudo descargar la planilla: HTTP {e.code})')
    except Exception as e:
        print(f'        (no se pudo descargar la planilla: {e})')
    return False

RE_MEGA = re.compile(r'mega\.nz/(?:folder|file)/([A-Za-z0-9_-]+)')
RE_URL  = re.compile(r'https?://[^\s,;]+')

REDES = {
    'instagram.com': 'Instagram',
    'x.com': 'X', 'twitter.com': 'X',
    'linkedin.com': 'LinkedIn',
    'tiktok.com': 'TikTok',
    'facebook.com': 'Facebook',
    'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
}

def _dominio(u):
    return re.sub(r'^https?://(www\.)?', '', u).split('/')[0].lower()

def _clasificar(urls):
    """Separa las URLs de una fila por tipo."""
    out = {'mega': [], 'nas': [], 'drive': [], 'publicaciones': [], 'otros': []}
    for u in urls:
        u = u.rstrip('.,;)')
        d = _dominio(u)
        if 'mega.nz' in d:            out['mega'].append(u)
        elif 'ug.link' in d:          out['nas'].append(u)
        elif 'google.com' in d:       out['drive'].append(u)
        elif any(r in d for r in REDES):
            nombre = next(v for k, v in REDES.items() if k in d)
            out['publicaciones'].append((nombre, u))
        else:                         out['otros'].append(u)
    return out

def leer(ruta):
    """Devuelve {id_de_carpeta_mega: datos}. Si falta pandas o el archivo, {}."""
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    try:
        import pandas as pd
    except ImportError:
        print('        (pandas no instalado: se omite la planilla. '
              'Instalar con: pip install pandas openpyxl)')
        return {}

    try:
        libro = pd.ExcelFile(ruta)
    except Exception as e:
        print(f'        (no se pudo abrir la planilla: {e})')
        return {}

    datos, filas_sin_cruce = {}, []
    for hoja in libro.sheet_names:
        try:
            df = pd.read_excel(libro, hoja).dropna(how='all')
        except Exception:
            continue
        for _, fila in df.iterrows():
            valores = {str(k).strip().upper(): v for k, v in fila.items() if pd.notna(v)}
            texto = ' '.join(str(v) for v in valores.values())
            urls = _clasificar(RE_URL.findall(texto))
            ids = [m for u in urls['mega'] for m in RE_MEGA.findall(u)]
            reg = {
                'nombre':   str(valores.get('NOMBRE COBERTURA', '')).strip().replace('\n', ' '),
                'area':     str(valores.get('AREA / SECRETARIA', '')).strip(),
                'descripcion_planilla': str(valores.get('DESCRIPCION', '')).strip(),
                'links_mega':  urls['mega'],
                'links_nas':   urls['nas'],
                'links_drive': urls['drive'],
                'publicaciones': urls['publicaciones'],
                'hoja': hoja,
            }
            if not ids:
                filas_sin_cruce.append((hoja, reg['nombre']))
                continue
            for i in ids:
                datos[i] = reg
    if filas_sin_cruce:
        print(f'        {len(filas_sin_cruce)} filas de la planilla sin link de MEGA')
    return datos

def enriquecer(filas, planilla):
    """Suma los datos de la planilla a cada operativo del índice. Devuelve cuántos cruzaron."""
    if not planilla:
        return 0
    n = 0
    for r in filas:
        m = RE_MEGA.search(r.get('link') or '')
        p = planilla.get(m.group(1)) if m else None
        if not p:
            continue
        n += 1
        r['nombre_planilla'] = p['nombre']
        r['area_planilla'] = p['area']
        # Un segundo link de MEGA sólo si es distinto del que ya tenemos
        otros = [u for u in p['links_mega'] if RE_MEGA.search(u).group(1) != m.group(1)]
        r['link_mega_alt'] = otros[0] if otros else ''
        r['link_nas']   = p['links_nas'][0] if p['links_nas'] else ''
        r['link_drive'] = p['links_drive'][0] if p['links_drive'] else ''
        r['publicaciones'] = '; '.join(f'{k}|{u}' for k, u in p['publicaciones'])
    return n
