# Proyecto Expedientes Marvel

Fuente de la colección de guías de lectura que se publica en `Desktop\Josema\Comics`.
El contenido vive en **datos** (YAML), el aspecto en **plantillas**, y un **generador** produce
las páginas HTML autónomas (funcionan sin conexión, con doble clic).

```
datos/
  coleccion.yaml               expedientes de la colección, portada y tabla de cruces
  expediente-*.yaml            el contenido de cada expediente
  auditoria.yaml               series cuya numeración se comprueba al generar
plantillas/
  expediente.html.j2           página de un expediente
  portada.html.j2              página principal (Expedientes Marvel.html)
  piezas.html.j2               ficha de serie, recuadro de evento y tramo
  recursos/                    CSS y JS compartidos, fuentes embebidas
generador/
  construir.py                 genera todo (y audita antes de escribir)
  auditoria.py                 comprobación de continuidad
herramientas/
  extraer.py                   migración inicial desde los HTML (ya no hace falta)
  comparar.py                  compara dos colecciones generadas
servicio/
  worker.js                    servicio en línea de las marcas (Cloudflare Worker + D1)
  esquema.sql                  tabla de la base de datos
  servidor_local.py            réplica local del servicio, para probar sin Cloudflare
  prueba_sincronizacion.py     prueba completa con dos navegadores (dos "dispositivos")
Generar expedientes.bat        doble clic: genera y publica en la carpeta Comics
```

## Generar

Doble clic en **`Generar expedientes.bat`**. Escribe directamente en `..\Comics`.

Antes de escribir, el generador comprueba la continuidad de 77 series y que los identificadores
de las entradas sean únicos. **Si encuentra un hueco no escribe nada** y dice qué falta.

Desde una consola, para generar en una carpeta de prueba (`salida\`):

```
.venv\Scripts\python generador\construir.py
.venv\Scripts\python herramientas\comparar.py salida ..\Comics     (¿cambió algo respecto a lo publicado?)
```

## Cambios habituales

Los textos admiten HTML en línea: `<em>`, `<strong>`, `<span class="nums">#1–12</span>`
(rango de números en un título) y `<span class="cap">…</span>` (capítulo resaltado en un orden de lectura).

**Corregir un número o un texto**: buscar la entrada en su `expediente-*.yaml` y editar el campo.

**Añadir una ficha de serie** dentro de un tramo, en `entradas:` y en su orden de lectura:

```yaml
- serie:
    prioridad: p2            # p1 esencial · p2 recomendado · (sin campo) opcional · p4 alterna
    titulo: Nombre de la serie <span class="nums">#1–12</span>
    creditos: Guionista · Dibujante · 2024
    descripcion:
    - Qué cuenta y por qué importa.
    continuidad:
    - viene: ◂ Viene del tramo 2.1
    - sigue: ▸ Los números #13–15 son capítulos de <em>Evento</em>
    etiqueta: {clase: t2, texto: Recomendado}     # t1 Esencial · t2 Recomendado · opcional · t4 Alterna
```

No hace falta poner `id`: el generador lo crea solo la primera vez y lo guarda en el YAML.

**Añadir un evento** (entre tramos, o dentro de un tramo):

```yaml
- evento:
    linea_marvel: true       # solo si es un evento de toda la línea Marvel (borde discontinuo)
    etiqueta: Evento · Marzo – mayo 2026
    titulo: Nombre del evento
    creditos: Guionista · Dibujante
    descripcion:
    - De qué va.
    apartados:
    - apartado: Antes de empezar
      texto: …
    - apartado: Orden de lectura
      texto: Evento #1 → <span class="cap">Serie #10</span> → Evento #2
    - apartado: Versión mínima
      texto: …
```

**Un expediente nuevo**: una entrada más en `coleccion.yaml` (nombre, archivo, colores) y su
archivo de datos copiando la estructura de uno existente. La portada, la cronología y el sistema de
lecturas lo incorporan solos.

## Regla importante: los `id`

Cada entrada tiene un `id` (por ejemplo `m1-b4-uncanny-x-men-500-512`). Es lo que guarda las
marcas de **Leyendo / Leído** en el navegador. **No lo cambies ni lo borres**, aunque cambies el
título: si una entrada pierde su `id`, su marca deja de verse. Si partes una ficha en dos, la parte
que conserva el contenido original se queda con el `id`; la nueva recibe uno automáticamente.

Las fichas que no son lecturas (como «Dónde están ahora») se excluyen solas; para excluir otra,
añade `marcable: false`.

## Marcas de lectura y sincronización

Las marcas se guardan siempre en el navegador, así que marcar funciona sin conexión. Si en
`coleccion.yaml` hay una `sincronizacion: url:`, el panel **Lecturas** ofrece crear un
**entorno**: un código de 20 caracteres (`xxxxx-xxxxx-xxxxx-xxxxx`) que identifica las marcas de
una persona. Con ese código, cualquier dispositivo ve y cambia las mismas marcas. Cada persona usa
su propio código, y nadie necesita registrarse.

- Cada cambio se envía al servicio un segundo después. También se sincroniza al abrir la página, al
  volver a ella, cada 90 s y cuando vuelve la red. Sin red, los cambios se quedan pendientes en el
  dispositivo (el punto del botón Lecturas lo indica) y se envían más tarde.
- Si dos dispositivos cambian la misma entrada, gana el cambio más reciente. Quitar una marca
  también se sincroniza.
- El punto del botón Lecturas indica el estado: verde, sincronizado; ámbar, cambios pendientes;
  círculo vacío, sin conexión; rojo, error. Sin entorno, no hay punto.
- Exportar e importar CSV sigue disponible como copia propia.

Para probar sin Cloudflare: `.venv\Scripts\python servicio\prueba_sincronizacion.py` arranca la
réplica local, genera la colección apuntando a ella y prueba dos Chrome sin ventana: crear y usar
un entorno, cambios sin red, conflictos y caída del servicio. Para probar a mano:
`.venv\Scripts\python servicio\servidor_local.py` y
`generador\construir.py --url-sincronizacion http://127.0.0.1:8787` (genera en `salida\`).

## Instalar el entorno (solo si se borra `.venv`)

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```
