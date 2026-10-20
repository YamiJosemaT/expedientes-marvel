# -*- coding: utf-8 -*-
"""Migracion de un solo uso: convierte los HTML publicados en datos YAML + recursos comunes.

Uso:  .venv\\Scripts\\python herramientas\\extraer.py "C:\\...\\Comics"

Se detiene con un error en cuanto encuentra una estructura que no sabe representar,
para que ninguna parte del contenido se pierda en silencio.
"""
import os
import re
import sys

import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMICS = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\josem\Desktop\Josema\Comics'

EXPEDIENTES = {
    'm1': ('Expediente Mutante/Expediente-Mutante-2001-2019.html', 'expediente-mutante-1.yaml'),
    'm2': ('Expediente Mutante/Expediente-Mutante-II-Krakoa-2019-2026.html', 'expediente-mutante-2.yaml'),
    'et': ('Expediente Eterno/Expediente-Eterno-2006-2026.html', 'expediente-eterno.yaml'),
    'gg': ('Expediente Guardianes/Expediente-Guardianes-2007-2026.html', 'expediente-guardianes.yaml'),
}


class Fallo(Exception):
    pass


def inner(t):
    return t.decode_contents().strip() if t is not None else None


def hijos(t):
    return [c for c in t.children if isinstance(c, Tag)]


def clases(t):
    return t.get('class') or []


def exigir(cond, msg):
    if not cond:
        raise Fallo(msg)


# ── piezas ──────────────────────────────────────────────────────────────
def serie(a, ctx):
    cl = clases(a)
    prio = [c for c in cl if c in ('p1', 'p2', 'p4')]
    extra = [c for c in cl if c not in ('serie', 'guest', 'p1', 'p2', 'p4')]
    exigir(not extra, '%s: clases desconocidas %s' % (ctx, extra))
    k = hijos(a)
    exigir(len(k) == 3 and 'stripe' in clases(k[0]) and k[1].name == 'div' and 'tag' in clases(k[2]),
           '%s: ficha de serie con hijos inesperados' % ctx)
    cuerpo, tag = k[1], k[2]
    e = {}
    if a.get('data-id'):
        e['id'] = a['data-id']
    if a.get('id'):
        e['ancla'] = a['id']
    if prio:
        e['prioridad'] = prio[0]
    if 'guest' in cl:
        e['aparicion'] = True
    orden = ['where', 'h3', 'cred', 'desc', 'cont']
    pos, descs = -1, []
    for c in hijos(cuerpo):
        tipo = 'h3' if c.name == 'h3' else (clases(c)[0] if c.name == 'p' and clases(c) else '?')
        exigir(tipo in orden, '%s: elemento desconocido <%s class="%s">' % (ctx, c.name, ' '.join(clases(c))))
        exigir(orden.index(tipo) >= pos and (tipo == 'desc' or orden.index(tipo) > pos),
               '%s: orden de elementos inesperado (%s)' % (ctx, tipo))
        pos = orden.index(tipo)
        if tipo == 'where':
            e['donde'] = inner(c)
        elif tipo == 'h3':
            e['titulo'] = inner(c)
        elif tipo == 'cred':
            e['creditos'] = inner(c)
        elif tipo == 'desc':
            descs.append(inner(c))
        elif tipo == 'cont':
            notas = []
            for s in c.children:
                if isinstance(s, NavigableString):
                    exigir(not s.strip(), '%s: texto suelto en nota de continuidad' % ctx)
                    continue
                exigir(s.name == 'span' and clases(s) in (['fwd'], ['back']), '%s: nota de continuidad rara' % ctx)
                notas.append({'sigue' if clases(s) == ['fwd'] else 'viene': inner(s)})
            e['continuidad'] = notas
    if descs:
        e['descripcion'] = descs
    tcl = [c for c in clases(tag) if c != 'tag']
    e['etiqueta'] = {'clase': tcl[0] if tcl else 'opcional', 'texto': inner(tag)}
    return {'serie': e}


def evento(a, ctx):
    cl = clases(a)
    extra = [c for c in cl if c not in ('evento', 'linea')]
    exigir(not extra, '%s: clases desconocidas %s' % (ctx, extra))
    e = {}
    if a.get('data-id'):
        e['id'] = a['data-id']
    if a.get('ancla') or a.get('id'):
        e['ancla'] = a['id']
    if 'linea' in cl:
        e['linea_marvel'] = True
    orden = ['ev-label', 'h3', 'cred', 'desc', 'orden']
    pos, descs, ords = -1, [], []
    for c in hijos(a):
        tipo = 'h3' if c.name == 'h3' else (clases(c)[0] if c.name == 'p' and clases(c) else '?')
        exigir(tipo in orden, '%s: elemento desconocido <%s class="%s">' % (ctx, c.name, ' '.join(clases(c))))
        exigir(orden.index(tipo) >= pos and (tipo in ('desc', 'orden') or orden.index(tipo) > pos),
               '%s: orden de elementos inesperado (%s tras %s)' % (ctx, tipo, orden[pos] if pos >= 0 else '-'))
        pos = orden.index(tipo)
        if tipo == 'ev-label':
            e['etiqueta'] = inner(c)
        elif tipo == 'h3':
            e['titulo'] = inner(c)
        elif tipo == 'cred':
            e['creditos'] = inner(c)
        elif tipo == 'desc':
            descs.append(inner(c))
        elif tipo == 'orden':
            lbl = c.find('span', class_='lbl', recursive=False)
            if lbl is not None:
                exigir(c.contents[0] is lbl, '%s: etiqueta de orden que no va al principio' % ctx)
                lbl_html = inner(lbl)
                lbl.extract()
                ords.append({'apartado': lbl_html, 'texto': inner(c)})
            else:
                ords.append({'texto': inner(c)})
    if descs:
        e['descripcion'] = descs
    if ords:
        e['apartados'] = ords
    return {'evento': e}


def entrada(a, ctx):
    cl = clases(a)
    if 'serie' in cl:
        return serie(a, ctx)
    if 'evento' in cl:
        return evento(a, ctx)
    raise Fallo('%s: <article> que no es ni serie ni evento' % ctx)


def tramo(t, ctx):
    k = hijos(t)
    head = k[0]
    exigir('tramo-head' in clases(head), '%s: tramo sin cabecera' % ctx)
    hk = hijos(head)
    exigir([x.name for x in hk] == ['span', 'h3', 'span'], '%s: cabecera de tramo rara' % ctx)
    num = inner(hk[0])
    m = re.fullmatch(r'Tramo (\d+\.\d+)', num)
    exigir(m, '%s: numero de tramo raro: %s' % (ctx, num))
    d = {'numero': m.group(1), 'titulo': inner(hk[1]), 'cuando': inner(hk[2])}
    resto = k[1:]
    if resto and 'tramo-nota' in clases(resto[0]):
        d['nota'] = inner(resto[0])
        resto = resto[1:]
    exigir(len(resto) == 1 and 'lista' in clases(resto[0]), '%s: tramo sin lista' % ctx)
    d['entradas'] = [entrada(a, '%s/%d' % (ctx, i)) for i, a in enumerate(hijos(resto[0]))]
    exigir(all(a.name == 'article' for a in hijos(resto[0])), '%s: algo que no es <article> en la lista' % ctx)
    return {'tramo': d}


def caja(div, ctx):
    k = hijos(div)
    if [x.name for x in k] == ['h2', 'p', 'ol']:
        return {'ruta': {'titulo': inner(k[0]), 'texto': inner(k[1]),
                         'pasos': [inner(li) for li in hijos(k[2])]}}
    return {'html': inner(div)}


def expediente(clave, ruta):
    s = BeautifulSoup(open(ruta, encoding='utf-8').read(), 'html.parser')
    d = {'clave': clave}
    d['titulo_pagina'] = str(s.title.string)
    d['descripcion_pagina'] = s.find('meta', attrs={'name': 'description'})['content']

    hdr = s.find('header', class_='top')
    d['cabecera'] = {
        'antetitulo': inner(hdr.find('p', class_='eyebrow')),
        'titulo': inner(hdr.find('h1')),
        'entradilla': inner(hdr.find('p', class_='lede')),
        'cifras': [{'valor': inner(x.find('b')), 'texto': inner(x.find('span'))} for x in hdr.find_all('div', class_='stat')],
    }

    nav = {}
    for a in s.select('nav.spine a'):
        yr = a.find('span', class_='yr')
        texto = ''.join(str(c) for c in a.contents if c is not yr).strip()
        nav[a['href'][1:]] = {'anio': inner(yr), 'texto': texto}
    exigir(nav.get('notas') == {'anio': 'Ap\u00e9ndice', 'texto': 'C\u00f3mo leerlo'}, '%s: enlace del apendice distinto' % clave)

    main = s.find('main')
    d['leyenda'] = None
    d['cajas'] = []
    d['bloques'] = []
    for c in hijos(main):
        cl = clases(c)
        if 'legend' in cl:
            d['leyenda'] = inner(c)
        elif 'ruta' in cl:
            d['cajas'].append(caja(c, clave))
        elif c.name == 'section' and 'bloque' in cl:
            bid = c['id']
            k = hijos(c)
            head = k[0]
            exigir('bloque-head' in clases(head), '%s/%s sin cabecera' % (clave, bid))
            num = inner(head.find('span', class_='bloque-num'))
            m = re.fullmatch(r'Bloque <b>(\d+)</b> \u00b7 (.+)', num)
            exigir(m, '%s/%s: numero de bloque raro: %s' % (clave, bid, num))
            exigir(int(m.group(1)) == int(bid[1:]), '%s/%s: numero de bloque no cuadra con el id' % (clave, bid))
            b = {'id': bid, 'fechas': m.group(2), 'titulo': inner(head.find('h2')),
                 'intro': inner(head.find('p', class_='bloque-intro')), 'navegacion': nav[bid], 'contenido': []}
            exigir(len(hijos(head)) == 3, '%s/%s: cabecera de bloque con elementos de mas' % (clave, bid))
            for i, x in enumerate(k[1:]):
                ctx = '%s/%s/%d' % (clave, bid, i)
                if x.name == 'div' and 'tramo' in clases(x):
                    b['contenido'].append(tramo(x, ctx))
                elif x.name == 'article':
                    b['contenido'].append(entrada(x, ctx))
                else:
                    raise Fallo('%s: elemento desconocido en el bloque' % ctx)
            d['bloques'].append(b)
        elif c.name == 'section' and 'cierre' in cl:
            exigir(c.get('id') == 'notas', '%s: apendice sin id notas' % clave)
            notas = []
            for n in hijos(c.find('div', class_='grid')):
                h4 = n.find('h4')
                h4.extract()
                notas.append({'titulo': inner(h4), 'html': inner(n)})
            d['apendice'] = {'titulo': inner(c.find('h2')), 'notas': notas}
        else:
            raise Fallo('%s: hijo de <main> desconocido: %s %s' % (clave, c.name, cl))
    exigir(set(nav) == {b['id'] for b in d['bloques']} | {'notas'}, '%s: la navegacion no coincide con los bloques' % clave)
    return d, s


# ── volcado YAML legible ────────────────────────────────────────────────
class Volcador(yaml.SafeDumper):
    pass


def _str(dumper, v):
    if '\n' in v:
        return dumper.represent_scalar('tag:yaml.org,2002:str', v, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', v)


Volcador.add_representer(str, _str)


def volcar(obj, ruta, cabecera):
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(cabecera)
        yaml.dump(obj, f, Dumper=Volcador, allow_unicode=True, sort_keys=False, width=100000, indent=2)


def main():
    datos = os.path.join(RAIZ, 'datos')
    recursos = os.path.join(RAIZ, 'plantillas', 'recursos')
    os.makedirs(recursos, exist_ok=True)
    fuentes = None
    for clave, (rel, nombre) in EXPEDIENTES.items():
        d, s = expediente(clave, os.path.join(COMICS, rel))
        estilos = s.find_all('style')
        exigir(len(estilos) == 2, '%s: se esperaban 2 bloques <style>' % clave)
        f = estilos[0].string
        exigir(fuentes is None or f == fuentes, '%s: las fuentes embebidas difieren' % clave)
        fuentes = f
        cab = ('# %s\n# Datos del expediente. Los textos admiten HTML en linea (<em>, <strong>, <span class="nums">...).\n'
               '# Las claves "id" de cada entrada NO se deben cambiar: son las que guardan las marcas de lectura.\n\n'
               % d['titulo_pagina'])
        volcar(d, os.path.join(datos, nombre), cab)
        n_ent = sum(1 for b in d['bloques'] for x in b['contenido']
                    for e in ([x] if 'tramo' not in x else x['tramo']['entradas']))
        print('%-3s -> datos/%-28s bloques: %d  entradas: %d' % (clave, nombre, len(d['bloques']), n_ent))
    with open(os.path.join(recursos, 'fuentes.css'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(fuentes.strip('\n') + '\n')
    print('fuentes.css: %d KB' % (len(fuentes) // 1024))


if __name__ == '__main__':
    try:
        main()
    except Fallo as e:
        print('ERROR DE EXTRACCION:', e)
        sys.exit(1)
