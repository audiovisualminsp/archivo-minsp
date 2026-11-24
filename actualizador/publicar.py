# -*- coding: utf-8 -*-
"""Sube archivos a un repositorio de GitHub usando su API.

No hace falta tener Git instalado: usa solo la librería estándar de Python.
La configuración se lee de config.txt (ver config-ejemplo.txt).
"""
import base64, json, urllib.request, urllib.error
from pathlib import Path

def leer_config(ruta):
    """config.txt con líneas clave = valor. Devuelve {} si no existe."""
    if not ruta.exists():
        return {}
    cfg = {}
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        k, v = linea.split('=', 1)
        cfg[k.strip()] = v.strip()
    return cfg

def _pedir(url, token, metodo='GET', datos=None):
    req = urllib.request.Request(url, method=metodo)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'indice-archivo-minsp')
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, cuerpo, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

def subir(archivo, cfg, destino=None):
    """Sube (o reemplaza) un archivo en el repositorio. Devuelve True si cambió."""
    archivo = Path(archivo)
    destino = destino or archivo.name
    base = f"https://api.github.com/repos/{cfg['owner']}/{cfg['repo']}/contents/{destino}"
    token = cfg['token']

    contenido = base64.b64encode(archivo.read_bytes()).decode('ascii')

    # Si ya existe, necesitamos su "sha" para reemplazarlo.
    sha = None
    try:
        actual = _pedir(base, token)
        sha = actual.get('sha')
        if actual.get('content', '').replace('\n', '') == contenido:
            return False                      # idéntico: no hace falta subirlo
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    datos = {'message': f'Actualización automática: {destino}', 'content': contenido}
    if sha:
        datos['sha'] = sha
    if cfg.get('branch'):
        datos['branch'] = cfg['branch']
    _pedir(base, token, 'PUT', datos)
    return True

def publicar(archivos, config_path):
    cfg = leer_config(Path(config_path))
    faltan = [k for k in ('owner', 'repo', 'token') if not cfg.get(k)]
    if faltan:
        print('        (no se publica: falta configurar ' + ', '.join(faltan) + ' en config.txt)')
        return
    for a in archivos:
        a = Path(a)
        if not a.exists():
            continue
        try:
            cambio = subir(a, cfg)
            print(f"        {'subido' if cambio else 'sin cambios'}: {a.name}")
        except urllib.error.HTTPError as e:
            detalle = e.read().decode('utf-8', 'replace')[:200]
            print(f'        ERROR al subir {a.name}: {e.code} {detalle}')
        except Exception as e:
            print(f'        ERROR al subir {a.name}: {e}')
