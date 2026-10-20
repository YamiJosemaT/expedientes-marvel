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


def guardar(ruta, cabecera, datos):
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(cabecera)
        yaml.dump(datos, f, Dumper=_Volcador, allow_unicode=True, sort_keys=False, width=100000, indent=2)
