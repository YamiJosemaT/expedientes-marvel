# -*- coding: utf-8 -*-
"""Compara la coleccion generada con otra (p. ej. la publicada) y dice si son equivalentes.

Uso:  .venv\\Scripts\\python herramientas\\comparar.py CARPETA_A CARPETA_B

Equivalente = mismos elementos, atributos (incluidos los data-id) y textos, mismos scripts,
y el mismo CSS salvo reglas que solo existen en una de las dos y estan en la lista de permitidas.
"""
import os
import re
import sys

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ARCHIVOS = ['Expedientes Marvel.html',
            'Expediente Mutante/Expediente-Mutante-2001-2019.html',
            'Expediente Mutante/Expediente-Mutante-II-Krakoa-2019-2026.html',
            'Expediente Eterno/Expediente-Eterno-2006-2026.html',
            'Expediente Guardianes/Expediente-Guardianes-2007-2026.html']
# reglas CSS que pueden estar en una version y no en otra sin cambiar nada visible
PERMITIDAS = re.compile(r'^(\.cruces|article\.evento, article\.serie\{scroll-margin|\.guest|\.where|\.swatch|article\.evento\.linea)')


def nodo(t):
    """Forma canonica de un elemento: (etiqueta, atributos, hijos), sin espacios irrelevantes."""
    hijos = []
    for c in t.children:
        if isinstance(c, Comment):
            continue
        if isinstance(c, NavigableString):
            s = re.sub(r'\s+', ' ', str(c))
            if s.strip():
                hijos.append(s.strip())
        elif isinstance(c, Tag):
            if c.name in ('style', 'script'):
                continue
            hijos.append(nodo(c))
    attrs = {k: (' '.join(v) if isinstance(v, list) else v) for k, v in t.attrs.items()}
    return (t.name, tuple(sorted(attrs.items())), tuple(hijos))


def primera_diferencia(a, b, ruta='html'):
    if a == b:
        return None
    if isinstance(a, str) or isinstance(b, str):
        return '%s: texto distinto\n    A: %r\n    B: %r' % (ruta, a if isinstance(a, str) else a[0], b if isinstance(b, str) else b[0])
    if a[0] != b[0] or a[1] != b[1]:
        return '%s: <%s %s> frente a <%s %s>' % (ruta, a[0], dict(a[1]), b[0], dict(b[1]))
    for i, (x, y) in enumerate(zip(a[2], b[2])):
        d = primera_diferencia(x, y, '%s>%s[%d]' % (ruta, x[0] if not isinstance(x, str) else '#texto', i))
        if d:
            return d
    return '%s: distinto numero de hijos (%d frente a %d)' % (ruta, len(a[2]), len(b[2]))


def reglas(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return [re.sub(r'\s+', ' ', r).strip() for r in re.findall(r'[^{}]+\{[^{}]*\}', css)]


def comparar(ra, rb):
    sa = BeautifulSoup(open(ra, encoding='utf-8').read(), 'html.parser')
    sb = BeautifulSoup(open(rb, encoding='utf-8').read(), 'html.parser')
    fallos = []
    if sa.title.string != sb.title.string:
        fallos.append('titulo distinto')
    da = sa.find('meta', attrs={'name': 'description'})['content']
    db = sb.find('meta', attrs={'name': 'description'})['content']
    if da != db:
        fallos.append('descripcion distinta')
    d = primera_diferencia(nodo(sa.body), nodo(sb.body), 'body')
    if d:
        fallos.append('DOM: ' + d)
    ea, eb = sa.find_all('style'), sb.find_all('style')
    if ea[0].string.strip() != eb[0].string.strip():
        fallos.append('fuentes embebidas distintas')
    ra_, rb_ = reglas(ea[1].string), reglas(eb[1].string)
    solo_a = [r for r in ra_ if r not in rb_ and not PERMITIDAS.match(r)]
    solo_b = [r for r in rb_ if r not in ra_ and not PERMITIDAS.match(r)]
    if solo_a or solo_b:
        fallos.append('CSS distinto: %d reglas solo en A, %d solo en B; p. ej. %s' % (len(solo_a), len(solo_b), (solo_a or solo_b)[0][:120]))
    # las reglas permitidas son independientes (selectores propios): su posicion no altera la cascada
    comunes_a = [r for r in ra_ if r in rb_ and not PERMITIDAS.match(r)]
    comunes_b = [r for r in rb_ if r in ra_ and not PERMITIDAS.match(r)]
    if comunes_a != comunes_b:
        fallos.append('CSS: las reglas comunes estan en distinto orden')
    ja = [s.string.strip() for s in sa.find_all('script')]
    jb = [s.string.strip() for s in sb.find_all('script')]
    if ja != jb:
        fallos.append('scripts distintos')
    ids_a = [t['data-id'] for t in sa.find_all(attrs={'data-id': True})]
    return fallos, len(ids_a)


def main():
    a, b = sys.argv[1], sys.argv[2]
    total = 0
    for rel in ARCHIVOS:
        fallos, n = comparar(os.path.join(a, rel), os.path.join(b, rel))
        total += len(fallos)
        print('%-62s %s' % (rel, 'EQUIVALENTE (%d data-id)' % n if not fallos else 'DIFERENTE'))
        for f in fallos:
            print('    - ' + f)
    print('\n' + ('Todo equivalente.' if not total else '%d diferencia(s).' % total))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
