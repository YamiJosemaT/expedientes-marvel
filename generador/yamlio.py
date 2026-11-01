# -*- coding: utf-8 -*-
"""Lectura y escritura de los YAML de datos conservando su formato y su cabecera de comentarios."""
import yaml


class _Volcador(yaml.SafeDumper):
    pass


def _str(dumper, v):
    if '\n' in v:
        return dumper.represent_scalar('tag:yaml.org,2002:str', v, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', v)


_Volcador.add_representer(str, _str)


def cargar(ruta):
    """Devuelve (cabecera_de_comentarios, datos)."""
    texto = open(ruta, encoding='utf-8').read()
    cabecera = []
    for linea in texto.split('\n'):
        if linea.startswith('#') or (cabecera and not linea.strip()):
            cabecera.append(linea)
            if not linea.strip():
                break
        else:
            break
    return '\n'.join(cabecera) + ('\n' if cabecera else ''), yaml.safe_load(texto)


def comentarios_en_linea(ruta):
    """Lineas con un comentario detras de un valor: un ' #' sin comillas corta ahi el texto en silencio.

    Hay que mirarlo en el archivo: al cargarlo, y mas aun al guardarlo, lo cortado ya no existe.
    """
    texto = open(ruta, encoding='utf-8').read()
    lineas = texto.split('\n')
    fin = {}
    for token in yaml.scan(texto):
        fin[token.end_mark.line] = max(fin.get(token.end_mark.line, 0), token.end_mark.column)
    return [(n + 1, lineas[n].strip()) for n, col in sorted(fin.items())
            if col and n < len(lineas) and lineas[n][col:].lstrip().startswith('#')]


def guardar(ruta, cabecera, datos):
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(cabecera)
        yaml.dump(datos, f, Dumper=_Volcador, allow_unicode=True, sort_keys=False, width=100000, indent=2)
