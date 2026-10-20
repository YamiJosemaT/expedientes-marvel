# -*- coding: utf-8 -*-
"""Replica local del servicio de lecturas (worker.js), para probar sin Cloudflare.

Uso:  .venv\\Scripts\\python servicio\\servidor_local.py [--puerto 8787] [--base lecturas-local.db]

Misma API, mismo esquema y mismas sentencias SQL que worker.js (Cloudflare D1 es SQLite).
Si cambias la logica en uno, cambiala tambien en el otro.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = 1
MAX_CUERPO = 512 * 1024
MAX_CAMBIOS = 3000
SOLAPE_MS = 5000
RE_ENTORNO = re.compile(r'^[a-z0-9]{5}(-[a-z0-9]{5}){3}$')
RE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,150}$')
ESTADOS = {'leido', 'leyendo', ''}
CAMPOS = ['f', 'x', 'b', 'tr', 't']

UPSERT = ('INSERT INTO marcas (entorno, id, estado, ts, datos, actualizado) VALUES (?1, ?2, ?3, ?4, ?5, ?6) '
          'ON CONFLICT (entorno, id) DO UPDATE SET estado = excluded.estado, ts = excluded.ts, '
          'datos = excluded.datos, actualizado = excluded.actualizado WHERE excluded.ts > marcas.ts')
CAMBIADAS = 'SELECT id, estado, ts, datos FROM marcas WHERE entorno = ?1 AND actualizado > ?2'

CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '86400',
        'Access-Control-Allow-Private-Network': 'true'}


def numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float('inf')


def crear_app(ruta_base):
    esquema = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'esquema.sql'), encoding='utf-8').read()
    db = sqlite3.connect(ruta_base, check_same_thread=False)
    db.executescript(esquema)
    candado = threading.Lock()

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def responder(self, obj, estado=200):
            cuerpo = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(estado)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            for k, v in CORS.items():
                self.send_header(k, v)
            self.send_header('Content-Length', str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_OPTIONS(self):
            self.send_response(204)
            for k, v in CORS.items():
                self.send_header(k, v)
            self.end_headers()

        def do_GET(self):
            if self.path == '/v1/salud':
                return self.responder({'ok': True, 'version': VERSION})
            self.responder({'error': 'Ruta no encontrada'}, 404)

        def do_POST(self):
            ruta = re.match(r'^/v1/entornos/([^/]+)/sincronizar$', self.path)
            if not ruta:
                return self.responder({'error': 'Ruta no encontrada'}, 404)
            entorno = ruta.group(1)
            if not RE_ENTORNO.match(entorno):
                return self.responder({'error': 'Código de entorno no válido'}, 400)
            largo = int(self.headers.get('Content-Length') or 0)
            if largo > MAX_CUERPO:
                return self.responder({'error': 'Petición demasiado grande'}, 413)
            try:
                cuerpo = json.loads(self.rfile.read(largo).decode('utf-8') or '{}')
            except ValueError:
                return self.responder({'error': 'JSON no válido'}, 400)
            cambios = cuerpo.get('cambios') if isinstance(cuerpo, dict) and isinstance(cuerpo.get('cambios'), dict) else {}
            if len(cambios) > MAX_CAMBIOS:
                return self.responder({'error': 'Demasiados cambios en una petición'}, 413)
            desde = cuerpo.get('desde') if numero(cuerpo.get('desde')) else 0

            ahora = int(time.time() * 1000)
            filas = []
            for id_, m in cambios.items():
                if not RE_ID.match(id_) or not isinstance(m, dict) or m.get('e') not in ESTADOS or not numero(m.get('ts')):
                    continue
                datos = json.dumps({k: m[k][:300] for k in CAMPOS if isinstance(m.get(k), str)}, ensure_ascii=False)
                filas.append((entorno, id_, m['e'], int(m['ts']), datos, ahora))
            with candado:
                if filas:
                    with db:
                        db.executemany(UPSERT, filas)
                res = db.execute(CAMBIADAS, (entorno, desde)).fetchall()
            marcas = {}
            for id_, estado, ts, datos in res:
                marcas[id_] = dict({'e': estado, 'ts': ts}, **json.loads(datos))
            self.responder({'marcas': marcas, 'cursor': ahora - SOLAPE_MS})

    return Manejador


class Servidor(ThreadingHTTPServer):
    def handle_error(self, peticion, direccion):
        if not isinstance(sys.exc_info()[1], ConnectionError):     # el navegador corto la conexion: no importa
            super().handle_error(peticion, direccion)


def arrancar(puerto=8787, base='lecturas-local.db'):
    """Arranca el servidor en un hilo y lo devuelve (para las pruebas)."""
    srv = Servidor(('127.0.0.1', puerto), crear_app(base))
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    return srv


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--puerto', type=int, default=8787)
    ap.add_argument('--base', default='lecturas-local.db')
    a = ap.parse_args()
    print('Servicio de lecturas local en http://127.0.0.1:%d  (base: %s)  Ctrl+C para parar' % (a.puerto, a.base))
    srv = Servidor(('127.0.0.1', a.puerto), crear_app(a.base))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
