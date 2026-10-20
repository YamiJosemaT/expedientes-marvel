# -*- coding: utf-8 -*-
"""Prueba de extremo a extremo de la sincronizacion de lecturas, sin Cloudflare.

Arranca servidor_local.py, genera la coleccion apuntando a el y abre dos Chrome sin ventana con
perfiles separados (dos "dispositivos") que se manejan por el protocolo de depuracion de Chrome.

Uso:  .venv\\Scripts\\python servicio\\prueba_sincronizacion.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import servidor_local  # noqa: E402

CHROME = next((p for p in [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
] if os.path.exists(p)), None)
PUERTO_SERVICIO = 8797


class Navegador:
    """Un Chrome sin ventana con su propio perfil, manejado por CDP."""

    def __init__(self, nombre, carpeta, puerto, url):
        self.nombre, self.n = nombre, 0
        perfil = os.path.join(carpeta, 'perfil-' + nombre)
        self.proc = subprocess.Popen([CHROME, '--headless=new', '--no-first-run', '--no-default-browser-check',
                                      '--disable-extensions', '--user-data-dir=' + perfil,
                                      '--remote-debugging-port=%d' % puerto, url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            self._conectar(puerto)
        except Exception:
            self.proc.kill()
            raise

    def _conectar(self, puerto):
        for _ in range(100):
            try:
                pags = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % puerto, timeout=1))
                pag = next(p for p in pags if p.get('type') == 'page')
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError('Chrome no arranco')
        self.ws = websocket.create_connection(pag['webSocketDebuggerUrl'], timeout=30, suppress_origin=True)
        self.errores = []
        self.cmd('Runtime.enable')
        self.cmd('Network.enable')
        self.esperar('document.readyState === "complete" && !!window.ExpedientesLecturas')

    def cmd(self, metodo, **params):
        self.n += 1
        self.ws.send(json.dumps({'id': self.n, 'method': metodo, 'params': params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get('method') == 'Runtime.exceptionThrown':
                self.errores.append(m['params']['exceptionDetails'].get('exception', {}).get('description', '?'))
            if m.get('id') == self.n:
                if 'error' in m:
                    raise RuntimeError(m['error'])
                return m['result']

    def js(self, expr):
        r = self.cmd('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
        if 'exceptionDetails' in r:
            raise RuntimeError('%s: %s' % (self.nombre, r['exceptionDetails']))
        return r['result'].get('value')

    def esperar(self, expr, seg=10):
        fin = time.time() + seg
        while time.time() < fin:
            try:
                if self.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.15)
        return False

    def navegar(self, url=None):
        self.js('window.__pagina_anterior = true')
        if url:
            self.cmd('Page.navigate', url=url)
        else:
            self.cmd('Page.reload', ignoreCache=True)
        if not self.esperar('!window.__pagina_anterior && document.readyState === "complete" && !!window.ExpedientesLecturas', 20):
            raise RuntimeError('%s: la pagina no termino de cargar' % self.nombre)

    def recargar(self):
        self.navegar()

    def red(self, conectado):
        self.cmd('Network.emulateNetworkConditions', offline=not conectado, latency=0,
                 downloadThroughput=-1, uploadThroughput=-1)

    def estado(self):
        return self.js('ExpedientesLecturas.estado()')

    def marca(self, id_):
        return self.js("(function(){var e=ExpedientesLecturas.estado().entorno;"
                       "var m=JSON.parse(localStorage.getItem(e?'expedientes-leidos:'+e:'expedientes-leidos')||'{}');"
                       "return m[%r]?m[%r].e:null})()" % (id_, id_))

    def pulsar(self, id_, estado):
        return self.js('(function(){var b=document.querySelector(\'article[data-id="%s"] .lect-btn[data-estado="%s"]\');'
                       'if(!b)return false;b.click();return true})()' % (id_, estado))

    def cerrar(self):
        try:
            self.ws.close()
        finally:
            self.proc.kill()
            self.proc.wait()


resultados = []


def comprobar(texto, ok):
    resultados.append(ok)
    print('  %s  %s' % ('OK ' if ok else 'FALLO', texto))


def main():
    if not CHROME:
        sys.exit('No encuentro Chrome')
    tmp = tempfile.mkdtemp(prefix='expedientes-prueba-')
    srv = servidor_local.arrancar(PUERTO_SERVICIO, os.path.join(tmp, 'marcas.db'))
    url_srv = 'http://127.0.0.1:%d' % PUERTO_SERVICIO
    destino = os.path.join(tmp, 'coleccion')
    subprocess.run([sys.executable, str(RAIZ / 'generador' / 'construir.py'), '--destino', destino,
                    '--url-sincronizacion', url_srv], check=True, stdout=subprocess.DEVNULL)
    pagina = Path(destino, 'Expediente Mutante', 'Expediente-Mutante-2001-2019.html').as_uri()
    portada = Path(destino, 'Expedientes Marvel.html').as_uri()
    a = b = None
    try:
        a = Navegador('A', tmp, 9341, pagina)
        b = Navegador('B', tmp, 9342, pagina)
        ids = a.js('[].map.call(document.querySelectorAll("article[data-id]"), function(x){return x.getAttribute("data-id")})')
        i1, i2, i3, i4, i5 = ids[0], ids[1], ids[2], ids[3], ids[4]

        print('\n1. Marcas antiguas (sin entorno, formato anterior)')
        a.js("localStorage.setItem('expedientes-leidos', JSON.stringify({%r:{e:'leido',f:'2026-10-01',x:'m1',b:'',tr:'',t:'x'},"
             "%r:{e:'leyendo',f:'2026-10-02',x:'m1',b:'',tr:'',t:'y'}}))" % (i1, i2))
        a.recargar()
        comprobar('se siguen viendo tras actualizar la pagina',
                  a.js('document.querySelectorAll("article.st-leido").length === 1 && document.querySelectorAll("article.st-leyendo").length === 1'))
        comprobar('sin entorno el estado es "local"', a.estado()['estado'] == 'local')

        print('\n2. Crear entorno en A subiendo lo local')
        codigo = a.js('ExpedientesLecturas.crearEntorno(true)')
        st = a.estado()
        comprobar('codigo con formato xxxxx-xxxxx-xxxxx-xxxxx (%s)' % codigo, bool(servidor_local.RE_ENTORNO.match(codigo or '')))
        comprobar('sincronizado y sin pendientes', st['estado'] == 'ok' and st['pendientes'] == 0 and st['marcas'] == 2)
        a.pulsar(i3, 'leido')
        comprobar('una marca nueva se envia sola (espera ~1,2 s)', a.esperar('ExpedientesLecturas.estado().pendientes === 0 && ExpedientesLecturas.estado().estado === "ok"', 6))

        print('\n3. B se une con el codigo')
        b.js("localStorage.setItem('expedientes-leidos', JSON.stringify({%r:{e:'leido',ts:Date.now(),f:'2026-10-20',x:'m1',b:'',tr:'',t:'z'}}))" % i4)
        b.recargar()
        b.js('ExpedientesLecturas.usarEntorno(%r, true)' % codigo.replace('-', '').upper())
        comprobar('B recibe las 3 marcas de A y sube la suya (4)', b.estado()['marcas'] == 4)
        comprobar('B las pinta', b.js('document.querySelectorAll("article.st-leido").length') == 3)
        a.js('ExpedientesLecturas.sincronizar()')
        comprobar('A recibe la de B', a.marca(i4) == 'leido')

        print('\n4. Quitar una marca en B llega a A')
        b.pulsar(i1, 'leido')
        b.esperar('ExpedientesLecturas.estado().pendientes === 0', 6)
        a.js('ExpedientesLecturas.sincronizar()')
        comprobar('en A ya no esta marcada', a.marca(i1) == '' and not a.js('document.querySelector(\'article[data-id="%s"]\').classList.contains("st-leido")' % i1))
        comprobar('el CSV de A no la incluye', i1 not in a.js('ExpedientesLecturas.exportCSV()'))

        print('\n5. A sin conexion')
        a.red(False)
        comprobar('el indicador pasa a "sin conexion"', a.esperar('ExpedientesLecturas.estado().estado === "sin-conexion"', 3))
        a.pulsar(i5, 'leido')
        a.pulsar(i2, 'leido')                       # conflicto: A cambia i2 sin red...
        comprobar('marcar sigue funcionando sin red', a.marca(i5) == 'leido' and a.js('document.querySelector(\'article[data-id="%s"]\').classList.contains("st-leido")' % i5))
        time.sleep(2)
        comprobar('quedan 2 cambios pendientes', a.estado()['pendientes'] == 2 and a.estado()['estado'] == 'sin-conexion')
        time.sleep(0.05)
        b.pulsar(i2, 'leyendo')                     # ...y B le quita la marca despues, con red: gana B
        b.esperar('ExpedientesLecturas.estado().pendientes === 0', 6)
        a.recargar()
        comprobar('al volver a abrir sin red, los cambios siguen pendientes', a.estado()['pendientes'] == 2 and a.marca(i5) == 'leido')

        print('\n6. A recupera la conexion')
        a.red(True)
        comprobar('se sincroniza sola al volver la red', a.esperar('ExpedientesLecturas.estado().estado === "ok" && ExpedientesLecturas.estado().pendientes === 0', 8))
        b.js('ExpedientesLecturas.sincronizar()')
        comprobar('B recibe la marca hecha sin red', b.marca(i5) == 'leido')
        comprobar('en el conflicto gana el cambio mas reciente (el de B) en los dos', a.marca(i2) == '' and b.marca(i2) == '')
        comprobar('A y B coinciden en todo', a.js('ExpedientesLecturas.exportCSV()').split('\r\n')[1:] and
                  sorted(a.js('ExpedientesLecturas.exportCSV()').split('\r\n')) == sorted(b.js('ExpedientesLecturas.exportCSV()').split('\r\n')))

        print('\n7. Servicio caido')
        srv.shutdown(); srv.server_close()
        b.pulsar(i3, 'leyendo')
        comprobar('B lo muestra como sin conexion y guarda el cambio', b.esperar('ExpedientesLecturas.estado().estado === "sin-conexion"', 20) and b.estado()['pendientes'] == 1)
        srv = servidor_local.arrancar(PUERTO_SERVICIO, os.path.join(tmp, 'marcas.db'))
        b.js('ExpedientesLecturas.sincronizar()')
        comprobar('al volver el servicio se envia', b.estado()['pendientes'] == 0 and b.estado()['estado'] == 'ok')

        print('\n8. Desconectar B y portada')
        b.js('ExpedientesLecturas.desconectar()')
        st = b.estado()
        comprobar('B queda en local con una copia de las marcas', st['entorno'] is None and st['estado'] == 'local' and st['marcas'] == a.estado()['marcas'])
        a.navegar(portada)
        sincronizada = a.esperar('ExpedientesLecturas.estado().estado === "ok"', 6)
        leidas = a.js('ExpedientesLecturas.exportCSV()').count(';Leído;')
        comprobar('A recibe en la portada el ultimo cambio de B', a.marca(i3) == 'leyendo')
        boton = a.js("document.querySelector('.lect-fab .fab-pct').textContent")
        comprobar('la portada carga, sincroniza y cuenta las leidas del entorno (%d; muestra "%s")' % (leidas, boton),
                  sincronizada and boton == '%d leídas' % leidas)
        comprobar('sin errores de JavaScript', not a.errores and not b.errores)
        for e in a.errores + b.errores:
            print('      ', e)
    finally:
        for n in (a, b):
            if n:
                n.cerrar()
        srv.shutdown()
        time.sleep(0.5)
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d de %d comprobaciones correctas' % (sum(resultados), len(resultados)))
    sys.exit(0 if all(resultados) else 1)


if __name__ == '__main__':
    main()
