# Proyecto Expedientes Marvel: contexto para Claude

Este archivo resume todo lo hablado y construido hasta el 2026-10-20 en una conversación larga
(iniciada en otro workspace). Léelo entero antes de tocar nada. El `README.md` del proyecto
explica el uso diario; aquí está además el porqué, las decisiones y lo pendiente.

## 1. Qué es y para quién

El usuario está leyendo cómics Marvel y hemos construido juntos una colección de **guías de lectura
("Expedientes")**: páginas HTML autónomas (abren con doble clic, funcionan sin conexión) con el
orden de lectura exacto de cada línea, series partidas donde un crossover se lleva sus números,
eventos con orden de lectura propio, y un sistema de marcas **Leyendo / Leído** por entrada.

- Habla **español**: responde y escribe todo (textos, comentarios, mensajes) en español.
- Usa **Chrome** (no Edge), en Windows 11. Más adelante, móvil y tablet Android.
- Lo que más le importa: **órdenes de lectura exactos y verificados con fuentes** (Marvel.com,
  Comic Book Herald, Crushing Krull, Marvel Fandom, CBR…). Ante la duda, verificar antes de
  afirmar; si algo no cuadra, decirlo. Ya hubo errores corregidos por no verificar (ver §7).
- Le gusta que se le expliquen las opciones con una recomendación, y luego decide él.
- No quiere depender de recordar hacer copias (de ahí la sincronización en línea, §6).

## 2. Ubicaciones

```
C:\Users\josem\Desktop\Josema\
  Proyecto Expedientes Marvel\     <- FUENTE (este proyecto)
  Comics\                          <- RESULTADO publicado (lo que abre el usuario)
    Expedientes Marvel.html                                   portada / índice
    Expediente Mutante\Expediente-Mutante-2001-2019.html      (m1)
    Expediente Mutante\Expediente-Mutante-II-Krakoa-2019-2026.html (m2)
    Expediente Eterno\Expediente-Eterno-2006-2026.html        (et)
    Expediente Guardianes\Expediente-Guardianes-2007-2026.html (gg)
    Expediente Jovenes Vengadores\Expediente-Jovenes-Vengadores-2005-2026.html (jv)
    */Older Versions\              copias anteriores a mano (Mutante I v0–v7, II v1–v5, Eterno v2, Guardianes v2)
```

**Nunca edites los HTML de `Comics` a mano**: se sobrescriben en la siguiente generación. Todo
cambio va en `datos/*.yaml` (contenido) o `plantillas/` (aspecto y scripts).

## 3. Flujo de trabajo

1. Editar `datos/expediente-*.yaml` o `datos/coleccion.yaml`.
2. Generar en `salida\` y comprobar:
   ```
   .venv\Scripts\python generador\construir.py
   .venv\Scripts\python herramientas\comparar.py salida ..\Comics
   ```
3. Publicar: `.venv\Scripts\python generador\construir.py --destino ..\Comics`, o doble clic en
   `Generar expedientes.bat` (desde PowerShell: `& ".\Generar expedientes.bat"`; con `cmd /c` las
   comillas fallan).
4. Para cambios grandes de contenido, puedes guardar antes una copia en `Older Versions`
   (`<nombre> vN.html`, siguiente número libre).

`construir.py`:
- carga los datos y asigna `id` a las entradas nuevas (y lo escribe en su YAML con `yamlio`);
- comprueba que los ids son únicos y que las anclas de los cruces existen;
- renderiza y audita la continuidad de 77 series (`datos/auditoria.yaml`);
- **no escribe nada si hay problemas** (`--forzar` lo salta, no lo uses sin motivo).

Avisos de auditoría conocidos y correctos (no son errores):
- Uncanny X-Force vol.1 "con #19.1"; GotG vol.3 "con #0.1".
- Magneto (2014) #9–10 repetidos (preludio de AXIS).
- Immortal X-Men #9–10 repetidos (prólogo de Sins of Sinister).
- Imperial Guardians #1 repetido: el one-shot *Imperial War: Imperial Guardians #1* se cita en el
  recuadro de Imperial. Se pensó reformular ese texto, sin hacerlo.

Entorno: Python 3.13 en `.venv` (PyYAML, Jinja2, beautifulsoup4, websocket-client; ver
`requirements.txt`). **Node.js no está instalado.**

Git: el proyecto está en git (rama `main`) y en GitHub, repositorio **público**
https://github.com/YamiJosemaT/expedientes-marvel (subido el 2026-10-20).
- Autor configurado en el repo: `YamiJosemaT <345464977+YamiJosemaT@users.noreply.github.com>`.
  La credencial antigua «YamiJosema» (sin T) de GitHub for Visual Studio no es la suya actual.
- `.gitattributes` mantiene LF en todo y CRLF en el `.bat`; `.gitignore` excluye `.venv`,
  `salida`, cachés y `*.db`.
- Commits y push solo con su OK. El entorno de Claude Code tiene `GCM_INTERACTIVE=never`: si
  la credencial caduca, el usuario debe hacer `git push` desde su propia terminal para iniciar
  sesión en el navegador.
- `gh` no está instalado. En PowerShell, el mensaje de commit va en un archivo (`git commit -F`).
  El estado de Actions se puede consultar sin autenticación en la API pública
  (`api.github.com/repos/YamiJosemaT/expedientes-marvel/actions/runs`).

Web: **https://yamijosemat.github.io/expedientes-marvel/** (GitHub Pages, Source = GitHub
Actions, desde el 2026-10-20). `.github/workflows/pages.yml` genera en cada push a `main`, falla si
`construir.py` modifica `datos/` (ids sin guardar), copia la portada a `index.html` y publica. Es
otro origen distinto de `file://`, así que tiene su propio localStorage: las marcas se comparten
entre la web y `Comics` solo a través del entorno.

## 4. Regla de oro: los `id`

Cada entrada marcable lleva `id` con formato `{exp}-{bloque}-{slug(título)}`, p. ej.
`m1-b4-uncanny-x-men-500-512` (exp: m1, m2, et, gg). Es la clave de las marcas de lectura
guardadas por el usuario. **No cambies ni borres un `id`**, aunque cambie el título o la entrada
se mueva de bloque o de expediente. Al partir una ficha en dos, la parte que conserva el contenido
original se queda el `id`; la nueva recibe uno automáticamente al generar. Hay 283 entradas
marcables (m1 116, m2 80, et 15, gg 36, jv 36).

Entradas movidas: `construir.py` detecta las que están en un expediente o bloque distinto del que
indica su `id` y las inyecta en `lecturas.js` como `REUBICADAS` (`{id: 'exp-bloque'}`). La portada
cuenta el progreso por ubicación real (`ubicacion(id)`), no por el prefijo. Ahora solo hay una:
`m1-b8-house-of-x-powers-of-x` → `m2-b1` (HoX/PoX se movió al Mutante II el 2026-10-20). Los recuadros «Dónde están ahora» / frontera de la guía no son
marcables; para excluir otra entrada: `marcable: false`.

## 5. Arquitectura

```
datos/
  coleccion.yaml        anio_inicio 2001, anio_final 2026 ("hoy"), sincronizacion.url,
                        expedientes (clave, datos, archivo, nombre, nombre_corto, subtitulo, periodo,
                        resumen, numeros_aprox, tema_clave, acento{claro, claro_suave, oscuro, oscuro_suave}),
                        portada (textos de la página índice), cruces (eventos presentes en varios
                        expedientes: evento, anio, enlaces[{expediente, ancla, texto}], nota)
  expediente-*.yaml     clave, titulo_pagina, descripcion_pagina, cabecera{antetitulo, titulo, entradilla,
                        cifras[{valor, texto}]}, leyenda (html), cajas[{ruta:{titulo,texto,pasos}} | {html}],
                        bloques[{id, fechas, titulo, intro, navegacion{anio,texto},
                                 contenido:[{tramo:{numero,titulo,cuando,nota?,entradas}} | {serie} | {evento}]}],
                        apendice{titulo, notas[{titulo, html}]}
  auditoria.yaml        por expediente: series [{reglas[{alias, vol?, bloques?, rango?}], esperado[[lo, hi|null]]}]
generador/
  construir.py          generación + auditoría (inyecta '__EXP__' y '__SYNC_URL__' en lecturas.js)
  auditoria.py          auditar(html, series) -> (filas, huecos)
  yamlio.py             cargar/guardar YAML conservando la cabecera de comentarios (estilo literal para multilínea)
plantillas/
  expediente.html.j2, portada.html.j2, piezas.html.j2 (macros serie/evento/entrada/tramo)
  recursos/ fuentes.css (woff2 en base64, 521 KB), comun.css.j2, tema.js.j2, indice.css.j2,
            lecturas.css, lecturas.js, portada-lecturas.css
herramientas/
  comparar.py           equivalencia de dos colecciones (DOM, data-id, scripts, reglas CSS y su orden)
  extraer.py            migración inicial HTML -> YAML (ya usada, no hace falta)
servicio/               sincronización en línea (§6)
```

Campos de una **serie**: `id`, `ancla?`, `prioridad?` (p1 esencial · p2 recomendado · sin campo
opcional · p4 alterna), `aparicion?` (ficha "guest": aparición en serie ajena, usado en Eterno y Jóvenes Vengadores),
`donde?`, `titulo`, `creditos`, `descripcion[]`, `continuidad[{sigue | viene}]`,
`etiqueta{clase t1|t2|t4|opcional, texto}`.

Campos de un **evento**: `id?`, `ancla?`, `linea_marvel?` (evento de toda la línea: borde
discontinuo), `etiqueta`, `titulo`, `creditos?`, `descripcion[]`, `apartados[{apartado?, texto}]`.
Apartados habituales de un evento de línea: «Antes de empezar», «Orden de lectura», «Versión
mínima», «Prescindible», «Después».

HTML en línea permitido en textos: `<em>`, `<strong>`, `<span class="nums">#1–12</span>` (rango en
títulos), `<span class="cap">…</span>` (capítulo de la propia línea dentro de un orden de lectura).

HTML generado (por si hay que tocar CSS/JS): `section.bloque#bN` > `div.bloque-head`
(`span.bloque-num`, `h2.bloque-title`, `p.bloque-intro`) + `div.tramo` (`tramo-head` con
`span.tramo-num`, `h3`, `span.tramo-when`; `p.tramo-nota?`; `div.lista`) + `article.evento[.linea]`.
`article.serie[ guest][ p1|p2|p4]` = `div.stripe` + div(`p.where?`, `h3`, `p.cred`, `p.desc*`,
`p.cont` con `.fwd`/`.back`) + `span.tag`. Las marcables llevan `data-id`.

Diseño: cada página es autónoma (fuentes embebidas, sin dependencias externas), con tokens de
color en `:root`, bloque oscuro por `prefers-color-scheme` y botón de tema (`[data-theme]`,
guardado en localStorage con un `tema_clave` por página). Color de acento por expediente en
`coleccion.yaml`.

## 6. Marcas de lectura y sincronización

`plantillas/recursos/lecturas.js` (mismo script en todas las páginas):
- botones Leyendo/Leído por entrada, barras de progreso por bloque y global, «ocultar lo leído»,
  panel flotante «Lecturas», exportar/importar CSV (`;`, BOM, columnas expediente, bloque, tramo,
  entrada, estado, fecha, id);
- localStorage compartido por todos los `file://` del mismo navegador (verificado en Chrome):
  - `expedientes-leidos`: marcas sin entorno;
  - `expedientes-leidos:<entorno>`, `expedientes-pendientes:<entorno>` (ids sin enviar),
    `expedientes-cursor:<entorno>`, `expedientes-sincronizacion` (`{entorno}`),
    `expedientes-ocultar-leidos`;
- marca = `{e: 'leido'|'leyendo'|'' (quitada), ts, f (fecha), x (exp), b, tr, t}`. Las marcas
  antiguas sin `ts` usan `Date.parse(f)`. Quitar una marca deja `e:''` (tombstone) para que la
  retirada se sincronice; el CSV y los recuentos la ignoran;
- `window.ExpedientesLecturas` = {exportCSV, importCSV, crearEntorno, usarEntorno, desconectar,
  sincronizar, estado} (lo usan las pruebas).

**Sincronización** (offline-first, decidida con el usuario): cada persona tiene un **entorno**,
un código aleatorio de 20 caracteres `xxxxx-xxxxx-xxxxx-xxxxx` (alfabeto sin l/o/0/1) que sirve
de llave, sin registro. Panel: «Crear mi entorno», «Ya tengo un código», «Sincronizar ahora»,
«Copiar código», «Desconectar» (deja copia local). Al crear o unirse, pregunta si subir las marcas
locales.
- Sincroniza al cargar, 1,2 s después de cada cambio, al volver la red, al volver a la pestaña
  (si pasaron más de 30 s) y cada 90 s. Sin red, los cambios quedan pendientes.
- Gana el `ts` más reciente por entrada.
- Indicador (punto en el botón): verde ok, ámbar pendiente, círculo vacío sin conexión/
  sincronizando, rojo error; sin entorno, sin punto.
- Solo se activa si `coleccion.yaml` → `sincronizacion.url` tiene valor. **Activa desde el
  2026-10-20** con `https://expediente-lecturas.josemapallero29.workers.dev`.

Despliegue en Cloudflare (cuenta gratuita del usuario, todo desde el panel web, sin Wrangler):
- Worker **`expediente-lecturas`**, en singular: con el plural da «error code: 1042», porque no existe.
  Código: `servicio/worker.js` pegado en «Edit code». Para actualizarlo hay que volver a pegarlo.
- D1 `expedientes-lecturas` (id `a32f1cb0-b6ba-4721-b56b-8757ddac8cfb`), enlazada como `DB`.
  El esquema se creó en su consola.
- Probado el 2026-10-20 con peticiones directas (8/8) y con dos Chrome sin ventana sobre `salida\` (7/7).
- Entornos de prueba que quedaron en D1 (se pueden borrar desde su consola):
  `prueb-aaaaa-aaaaa-aaaaa`, `9rdep-u3und-ycake-v6ahw` y `nxx36-h7k5k-cay55-4e2sw` (este último,
  de la prueba de la web).

Servicio (`servicio/`):
- `worker.js`: Cloudflare Worker (módulo ES) con D1 enlazada como `DB`.
  - `GET /v1/salud` devuelve `{ok, version:1}`.
  - `POST /v1/entornos/{codigo}/sincronizar` recibe `{cambios:{id:marca}, desde:cursor}` y
    devuelve `{marcas, cursor}`.
  - UPSERT con `WHERE excluded.ts > marcas.ts`. El cursor es `ahora - 5000` (solape de 5 s,
    idempotente).
  - CORS `*`; el cliente envía `Content-Type: text/plain` para evitar el preflight.
  - Límites: 512 KB por petición y 3000 cambios; ids `^[a-z0-9][a-z0-9-]{0,150}$`; campos a 300
    caracteres.
- `esquema.sql`: tabla `marcas(entorno, id, estado, ts, datos JSON, actualizado)`, PK
  (entorno, id), con índice (entorno, actualizado).
- `servidor_local.py`: réplica exacta con stdlib y sqlite3. **Si cambias la lógica en uno, cámbiala
  en el otro.** Arranque: `servidor_local.py --puerto 8787`. Generar contra ella:
  `construir.py --url-sincronizacion http://127.0.0.1:8787` (genera en `salida\`).
- `prueba_sincronizacion.py`: prueba de extremo a extremo con dos Chrome headless (perfiles
  separados, protocolo CDP con websocket-client). Cubre:
  - marcas antiguas, crear y usar un entorno;
  - tombstones;
  - offline con recarga y reconexión;
  - conflicto entre dispositivos;
  - caída del servicio, desconexión y portada.

  **Resultado: 24/24 OK.**

## 7. Contenido y decisiones editoriales

- **Mutante I (m1, 2001–2019)**, 8 bloques, de Morrison a House of X/Powers of X. Incluye:
  - Age of Apocalypse integrada a petición: el one-shot + miniserie de 2005 y la serie de 2012;
  - X-Termination con orden ajustado;
  - eventos de línea como Chaos War y Fear Itself;
  - Wolverine and the X-Men partido en varias fichas por los crossovers.

  Al principio el usuario pidió no tocar este volumen, pero después pidió verificarlo y
  corregirlo. Cámbialo solo cuando lo pida.
- **Mutante II (m2, 2019–2026)**, 7 bloques: Dawn of X → Reign of X → Destiny of X → Fall of X →
  From the Ashes → Age of Revelation → Shadows of Tomorrow. Incluye las tres Hellfire Gala,
  A.X.E., Sins of Sinister y The Last Annihilation (añadido a petición).
- **HoX/PoX abre el Mutante II** (primera ficha del bloque 1, ancla `hoxpox`, «Léelos antes que
  nada»), a petición del usuario. El Mutante I termina con un recuadro de frontera que enlaza
  con ella. Cifras: m1 26 eventos, m2 20.
- Las páginas de expediente tienen un botón «Inicio» fijo arriba a la izquierda (`inicio` en la
  plantilla: ruta relativa a la portada).
- **Eterno (et, 2006–2026)**: Gaiman/Romita Jr. → Knauf → Final Host → Gillen → A.X.E. →
  actualidad, con fichas de apariciones en series ajenas.
- **Guardianes (gg, 2007–2026)**: Annihilation: Conquest → Abnett & Lanning → Bendis → Gemas del
  Infinito → Cates/Ewing → Grootfall → Imperial (guionista **Jonathan Hickman**). Recoge los
  crossovers con otras líneas.
- **Jóvenes Vengadores (jv, 2005–2026)**, añadido el 2026-10-22 y centrado en **Wiccan y Hulkling**
  (Billy Kaplan y Teddy Altman), a petición del usuario: Heinberg/Cheung → eventos 2006–2010 →
  Children's Crusade → Gillen/McKelvie → New Avengers de Ewing → Empyre → Emperador y consorte →
  apariciones 2023–2024 → Imperial y *Wiccan: Witches' Road* (2025–2026) + *Raid of Ultron*.
  9 bloques, 36 entradas. Fuentes: listas de apariciones de Marvel Fandom (categoría
  `William_Kaplan_(Earth-616)/Appearances` y `Theodore_Altman_(Earth-616)/Appearances`, vía su API
  `api.php`, porque la web da 402/403) y Comic Book Herald (descargado con curl y user-agent de
  navegador). Solo incluye lo que mueve algo de la pareja; lo descartado está en su apéndice.
- **Portada** (`Expedientes Marvel.html`): índice, cronología 2001–2026 y tabla de 12 «cruces»
  (Civil War, Secret Invasion, War of Kings, Age of Ultron, Trial of Jean Grey, Black Vortex,
  Secret Wars, Civil War II, Empyre, The Last Annihilation, A.X.E., Imperial).
- Criterios:
  - una serie larga se parte justo donde un crossover se lleva sus números;
  - cada parte indica de dónde viene y adónde sigue (`continuidad`);
  - los números que van dentro de un evento se citan en el recuadro del evento.
- Correcciones hechas tras verificar con fuentes (no reintroducirlas):
  - Imperial es de Hickman;
  - The Black Vortex tiene 13 partes;
  - orden de Dark Web corregido;
  - hueco de X-Men vol.6 #23–25 en torno a la Hellfire Gala 2023 resuelto.
- X-Factor vol.3 #25–27 **no** es un hueco: están dentro del recuadro de Messiah Complex. El usuario
  no los encontró; se ofreció enlazar automáticamente los nombres de evento de las notas de
  continuidad con su recuadro.

## 8. Trampas técnicas ya conocidas

- En la herramienta Bash (Git Bash), los heredocs convierten `\\n`, `\\u`… en caracteres reales y
  rompen el código. Para escribir código con barras invertidas usa las herramientas Write/Edit.
- En YAML, los valores que contienen `: ` van entre comillas.
- Plantillas Jinja con el `Undefined` normal (con StrictUndefined fallan los campos opcionales).
  Placeholders en recursos: `{{ NOMBRE }}` (con `%` se rompía el CSS).
- Pruebas con Chrome headless:
  - usar **siempre** `--user-data-dir` propio, porque ejecutar `chrome.exe` sin él abre pestañas
    en el Chrome real del usuario;
  - con websocket-client, `suppress_origin=True`;
  - tras recargar, esperar a un marcador de página nueva;
  - matar las instancias huérfanas filtrando por `remote-debugging-port`.
- Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## 9. Pendiente

1. **Servicio desplegado y publicado (2026-10-20)** (ver §6). Falta que el usuario lo pruebe
   en su PC y en el móvil (en el móvil, a través de la web de GitHub Pages). Plan gratuito: unas 100k peticiones al día, de sobra. Pendiente
   opcional: código QR del entorno para pasarlo al móvil.
2. **Fase 2: APK Android independiente** («sin tener que registrarme ni nada»): empaquetar las
   páginas en una app. Comprobar antes qué toolchain hace falta (no hay Android SDK ni Node
   instalados). Tras el APK, probar en móvil y tablet.
3. Ofertas sin respuesta del usuario:
   - autoenlazar nombres de evento en las notas de continuidad;
   - reformular la mención del one-shot Imperial Guardians #1.
