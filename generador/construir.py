# -*- coding: utf-8 -*-
"""Genera la coleccion Expedientes Marvel a partir de datos/ y plantillas/.

Uso:
    .venv\\Scripts\\python generador\\construir.py                  -> genera en la carpeta "salida" del proyecto
    .venv\\Scripts\\python generador\\construir.py --destino DIR    -> genera en DIR (p. ej. la carpeta Comics)
    --forzar  escribe aunque la auditoria encuentre huecos

Pasos: carga datos -> asigna id a las entradas nuevas (y lo guarda en su YAML) -> comprueba ids
unicos -> renderiza -> audita la continuidad -> escribe los archivos si todo esta bien.
"""
import argparse
import os
import re
import sys
import unicodedata
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auditoria  # noqa: E402
import yamlio  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, 'datos')
PLANTILLAS = os.path.join(RAIZ, 'plantillas')
RECURSOS = os.path.join(PLANTILLAS, 'recursos')
EN_LETRAS = {1: 'un', 2: 'dos', 3: 'tres', 4: 'cuatro', 5: 'cinco', 6: 'seis', 7: 'siete', 8: 'ocho', 9: 'nueve', 10: 'diez'}


def leer(nombre):
    return open(os.path.join(RECURSOS, nombre), encoding='utf-8').read()


def slug(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = s.replace('&amp;', '&').replace('–', '-').replace('—', '-').replace('→', '-')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:70].rstrip('-')


def entradas(bloque):
    """Todas las entradas (serie o evento) de un bloque, en orden de lectura."""
    for c in bloque['contenido']:
        if 'tramo' in c:
            for x in c['tramo']['entradas']:
                yield x
        else:
            yield c


def cuerpo(x):
    return x['serie'] if 'serie' in x else x['evento']


def marcable(x):
    e = cuerpo(x)
    if e.get('marcable') is False:
        return False
    return 'Frontera de la guía' not in (e.get('etiqueta') or '')


def asignar_ids(exp, datos):
    """Da id a las entradas que no lo tienen. Devuelve la lista de ids nuevos."""
    usados = {cuerpo(x)['id'] for b in datos['bloques'] for x in entradas(b) if cuerpo(x).get('id')}
    nuevos = []
    for b in datos['bloques']:
        for x in entradas(b):
            e = cuerpo(x)
            if e.get('id') or not marcable(x):
                continue
            base = '%s-%s-%s' % (exp['clave'], b['id'], slug(e.get('titulo', 'entrada')) or 'entrada')
            uid, n = base, 2
            while uid in usados:
                uid, n = '%s-%d' % (base, n), n + 1
            usados.add(uid)
            datos_e = {'id': uid}
            datos_e.update(e)
            e.clear()
            e.update(datos_e)                       # el id queda como primera clave, para que se vea al editar
            nuevos.append(uid)
    return nuevos


def anios(fechas, anio_final):
    ys = [int(y) for y in re.findall(r'(?:19|20)\d\d', fechas)]
    if 'hoy' in fechas:
        ys.append(anio_final)
    return min(ys), max(ys)


def main():
    ap = argparse.ArgumentParser(description='Genera la coleccion Expedientes Marvel.')
    ap.add_argument('--destino', default=os.path.join(RAIZ, 'salida'))
    ap.add_argument('--forzar', action='store_true', help='escribir aunque la auditoria encuentre huecos')
    ap.add_argument('--url-sincronizacion', help='servicio de lecturas a usar en vez del de coleccion.yaml (pruebas)')
    args = ap.parse_args()

    env = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    env.filters['numero_en_letras'] = lambda n: EN_LETRAS.get(n, str(n))

    _, col = yamlio.cargar(os.path.join(DATOS, 'coleccion.yaml'))
    _, reglas = yamlio.cargar(os.path.join(DATOS, 'auditoria.yaml'))
    rec = {'fuentes': leer('fuentes.css'), 'lecturas_css': leer('lecturas.css'),
           'portada_lecturas': leer('portada-lecturas.css').rstrip('\n')}
    url_sync = args.url_sincronizacion
    if url_sync is None:
        url_sync = (col.get('sincronizacion') or {}).get('url') or ''
    if not re.match(r"^(https?://[^\s'\"\\]+)?$", url_sync):
        sys.exit('url de sincronizacion no valida: %r' % url_sync)
    lecturas_js = leer('lecturas.js').replace("'__SYNC_URL__'", "'%s'" % url_sync)
    a0, a1 = col['anio_inicio'], col['anio_final']

    salidas, problemas, todos_ids = {}, 0, {}
    exps = []
    for exp in col['expedientes']:
        ruta = os.path.join(DATOS, exp['datos'])
        cab, datos = yamlio.cargar(ruta)
        nuevos = asignar_ids(exp, datos)
        if nuevos:
            yamlio.guardar(ruta, cab, datos)
            print('  ids nuevos en %s: %s' % (exp['datos'], ', '.join(nuevos)))
        for b in datos['bloques']:
            for x in entradas(b):
                uid = cuerpo(x).get('id')
                if uid:
                    if uid in todos_ids:
                        print('ERROR: id repetido %s (en %s y %s)' % (uid, todos_ids[uid], exp['clave']))
                        problemas += 1
                    todos_ids[uid] = exp['clave']

        estilos = env.get_template('recursos/comun.css.j2').render(acento=exp['acento']).rstrip('\n')
        tema = env.get_template('recursos/tema.js.j2').render(tema_clave=exp['tema_clave'])
        inicio = '../' * exp['archivo'].count('/') + quote(col['portada']['archivo'])
        html_exp = env.get_template('expediente.html.j2').render(
            x=datos, recursos=rec, estilos=estilos, tema_js=tema, inicio=inicio,
            lecturas_js=lecturas_js.replace("'__EXP__'", "'%s'" % exp['clave']))
        salidas[exp['archivo']] = html_exp

        filas, huecos = auditoria.auditar(html_exp, reglas.get(exp['clave'], []))
        problemas += huecos
        avisos = [f for f in filas if not f[2].startswith(('completa', 'sin huecos'))]
        print('%-24s %3d series vigiladas | huecos: %d%s' % (exp['nombre'], len(filas), huecos,
                                                             '' if not avisos else ' | avisos: %d' % len(avisos)))
        for f in avisos:
            print('     %-28s %-12s %s' % f)

        # datos para la portada
        href = quote(exp['archivo'])
        bloques = []
        for i, b in enumerate(datos['bloques']):
            y0, y1 = anios(b['fechas'], a1)
            num = '%02d' % int(b['id'][1:])
            bloques.append({
                'id': b['id'], 'num': num, 'titulo': b['titulo'], 'fechas': b['fechas'], 'href': href + '#' + b['id'],
                'anios': str(y0) if y0 == y1 else '%d–%s' % (y0, 'hoy' if 'hoy' in b['fechas'] else y1),
                'col_ini': y0 - a0 + 1, 'col_fin': y1 - a0 + 2, 'fila': 1 + i % 2,
                'total': sum(1 for x in entradas(b) if cuerpo(x).get('id')),
            })
        e = dict(exp)
        e.update({'href': href, 'cifras': datos['cabecera']['cifras'], 'bloques': bloques,
                  'total': sum(b['total'] for b in bloques)})
        exps.append(e)

    # portada
    p = col['portada']
    cruces = []
    for c in col['cruces']:
        c = dict(c)
        c['enlaces'] = [dict(l, href=quote(next(x['archivo'] for x in col['expedientes'] if x['clave'] == l['expediente'])) + '#' + l['ancla'])
                        for l in c['enlaces']]
        cruces.append(c)
    anios_eje = [{'col': y - a0 + 1, 'texto': str(y) if y in (a0, a1) or y % 5 == 0 else "'%02d" % (y % 100)}
                 for y in range(a0, a1 + 1)]
    estilos_portada = env.get_template('recursos/indice.css.j2').render(expedientes=col['expedientes'], n_anios=a1 - a0 + 1).rstrip('\n')
    salidas[p['archivo']] = env.get_template('portada.html.j2').render(
        portada=p, exps=exps, cruces=cruces, anios=anios_eje, recursos=rec, estilos=estilos_portada,
        tema_js=env.get_template('recursos/tema.js.j2').render(tema_clave=p['tema_clave']),
        lecturas_js=lecturas_js.replace("'__EXP__'", "''"),
        total_bloques=sum(len(e['bloques']) for e in exps), total_entradas=sum(e['total'] for e in exps),
        total_numeros='~' + format(sum(e['numeros_aprox'] for e in col['expedientes']), ',').replace(',', '.'))

    # anclas de la tabla de cruces
    for c in cruces:
        for l in c['enlaces']:
            archivo = next(x['archivo'] for x in col['expedientes'] if x['clave'] == l['expediente'])
            if ('id="%s"' % l['ancla']) not in salidas[archivo]:
                print('ERROR: el cruce "%s" apunta a #%s, que no existe en %s' % (c['evento'], l['ancla'], archivo))
                problemas += 1

    print('%d entradas marcables en total' % len(todos_ids))
    if problemas and not args.forzar:
        print('\nNO SE HA ESCRITO NADA: hay %d problema(s). Corrígelos o usa --forzar.' % problemas)
        return 1
    for rel, contenido in salidas.items():
        destino = os.path.join(args.destino, rel)
        os.makedirs(os.path.dirname(destino) or args.destino, exist_ok=True)
        with open(destino, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
    print('\nGenerados %d archivos en %s' % (len(salidas), args.destino))
    return 0


if __name__ == '__main__':
    sys.exit(main())
