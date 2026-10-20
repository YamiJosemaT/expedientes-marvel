# -*- coding: utf-8 -*-
"""Auditoria de continuidad sobre el HTML generado.

Solo cuenta como "colocado" un numero que aparece en un titulo de ficha (h3), en su linea
de creditos (p.cred) o en un apartado de evento (p.orden). Las notas de continuidad y las
descripciones NO cuentan: avisan, pero no colocan el numero en ningun sitio de lectura.
"""
import html
import re

_ARTICULO = re.compile(r'<article class="(?:serie[^"]*|evento[^"]*)"[^>]*>(.*?)</article>', re.S)
_BLOQUE = re.compile(r'<section class="bloque" id="b(\d+)">(.*?)</section>', re.S)


def _limpiar(s):
    s = re.sub(r'<span class="lbl">(.*?)</span>', r'\1 | ', s)          # la etiqueta de apartado no se pega al texto
    s = re.sub(r'<span class="nums">(?=[^#])', ' | ', s)                 # ni el titulo de la ficha a su lista de series
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', html.unescape(s))


def _tramos(xs):
    out, ini = [], None
    for i, x in enumerate(xs):
        if ini is None:
            ini = x
        if i + 1 == len(xs) or xs[i + 1] != x + 1:
            out.append('#%d' % ini if ini == x else '#%d-%d' % (ini, x))
            ini = None
    return ', '.join(out)


def auditar(html_expediente, series):
    """Devuelve (filas, huecos): filas = [(serie, colocado, estado)], huecos = numero de series con huecos."""
    cobertura = {s['serie']: {} for s in series}
    puntos = {}
    for sec in _BLOQUE.finditer(html_expediente):
        blk, cuerpo = int(sec.group(1)), sec.group(2)
        for ai, art in enumerate(_ARTICULO.finditer(cuerpo)):
            a = art.group(1)
            textos = [_limpiar(t) for t in re.findall(r'<h3>(.*?)</h3>', a, re.S) +
                      re.findall(r'<p class="cred">(.*?)</p>', a, re.S) +
                      re.findall(r'<p class="orden">(.*?)</p>', a, re.S)]
            for t in textos:
                vistos = set()                       # cada coincidencia de texto cuenta para una sola serie
                for s in series:
                    for r in s['reglas']:
                        vol, bloques = r.get('vol'), r.get('bloques') or []
                        lo, hi = r.get('rango') or (1, 10 ** 6)
                        patron = (re.escape(r['alias']) +
                                  r'(?: vol\. (\d))? #(\d+)(\.\d+)?(?:–(\d+))?((?:\s*(?:,|→)\s*#\d+(?:–\d+)?)*)')
                        for m in re.finditer(patron, t):
                            if (m.start(), m.end()) in vistos:
                                continue
                            if re.search(r"[A-Za-z\-/:'&.]\s?$", t[max(0, m.start() - 3):m.start()]):
                                continue                     # parte de un titulo compuesto (Dark X-Men, Laura Kinney: Wolverine...)
                            mv = m.group(1)
                            if mv is not None and mv != vol:
                                continue
                            if mv is None and blk not in bloques:
                                continue
                            a1, b1 = int(m.group(2)), int(m.group(4) or m.group(2))
                            if not m.group(3) and not (lo <= a1 and b1 <= hi):
                                continue                     # un numero punto (#0.1, #19.1) no se filtra por rango
                            vistos.add((m.start(), m.end()))
                            sitio = 'b%d#%d' % (blk, ai)
                            if m.group(3):
                                puntos.setdefault(s['serie'], set()).add(m.group(2) + m.group(3))
                            else:
                                for i in range(a1, b1 + 1):
                                    cobertura[s['serie']].setdefault(i, set()).add(sitio)
                            for x, y in re.findall(r'#(\d+)(?:–(\d+))?', m.group(5) or ''):
                                for i in range(int(x), int(y or x) + 1):
                                    cobertura[s['serie']].setdefault(i, set()).add(sitio)

    filas, huecos = [], 0
    for s in series:
        c = cobertura[s['serie']]
        if not c:
            filas.append((s['serie'], '-', 'NO APARECE'))
            huecos += 1
            continue
        esperado = set()
        abierta = False
        for lo, hi in s['esperado']:
            if hi is None:
                abierta = True
                hi = max(c)
            esperado |= set(range(lo, hi + 1))
        faltan = sorted(esperado - set(c))
        repetidos = sorted(i for i, sitios in c.items() if len(sitios) > 1)
        msg = []
        if faltan:
            msg.append('FALTAN ' + _tramos(faltan))
            huecos += 1
        if repetidos:
            msg.append('repetidos ' + _tramos(repetidos))
        if s['serie'] in puntos:
            msg.append('con ' + ', '.join('#' + p for p in sorted(puntos[s['serie']])))
        if not msg:
            msg.append('sin huecos (en curso)' if abierta else 'completa')
        filas.append((s['serie'], '#%d-%d' % (min(c), max(c)), '; '.join(msg)))
    return filas, huecos
