/* Lecturas: marcas de "leyendo" / "leido" por entrada.
   Funcionan siempre sin conexion (copia local en el navegador) y, si hay un entorno configurado,
   se sincronizan con el servicio de lecturas cuando hay red. Se exportan e importan en CSV.

   Almacenamiento local (compartido por todas las paginas de la coleccion):
     expedientes-leidos                 marcas sin entorno (solo en este dispositivo)
     expedientes-leidos:<entorno>       marcas de un entorno sincronizado
     expedientes-pendientes:<entorno>   ids cambiados que el servicio aun no ha recibido
     expedientes-cursor:<entorno>       hasta donde ha recibido este dispositivo del servicio
     expedientes-sincronizacion         { entorno } configurado en este dispositivo
   Cada marca: { e: 'leido' | 'leyendo' | '' (quitada), ts: ms del cambio, f, x, b, tr, t } */
(function () {
  var EXP = '__EXP__';
  var URL_SERVICIO = '__SYNC_URL__'.replace(/\/+$/, '');
  var K_LOCAL = 'expedientes-leidos', K_CONF = 'expedientes-sincronizacion', K_HIDE = 'expedientes-ocultar-leidos';
  var NOMBRES = { m1: 'Expediente Mutante I', m2: 'Expediente Mutante II', et: 'Expediente Eterno', gg: 'Expediente Guardianes', jv: 'Expediente Jóvenes Vengadores' };
  // Entradas que se movieron de sitio conservando su id: { id: 'expediente-bloque' donde estan ahora }
  var REUBICADAS = {/*__REUBICADAS__*/};
  var ALFABETO = 'abcdefghijkmnpqrstuvwxyz23456789';   // sin l, o, 0, 1: no se confunden al escribirlo a mano
  var CADA_MS = 90000, ESPERA_MS = 1200, TIEMPO_MS = 15000;

  function hoy() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  // "expediente-bloque-..." de una entrada segun donde esta ahora, no segun su id
  function ubicacion(id) { return REUBICADAS[id] ? REUBICADAS[id] + '-' : id; }
  function leerJSON(k, def) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? def : v; } catch (e) { return def; } }
  function guardarJSON(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function pct(r, n) { return n ? Math.round(100 * r / n) : 0; }
  function bar(r, n) {
    return '<span class="pbar" role="img" aria-label="' + pct(r, n) + '% leído"><span style="width:' + pct(r, n) + '%"></span></span>';
  }
  function texto(r, n, l) {
    return r + ' de ' + n + ' entradas leídas' + (l ? ' · ' + l + ' en curso' : '');
  }
  function limpio(s) { return (s || '').replace(/\s+/g, ' ').trim(); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function plural(n, s) { return n + ' ' + s + (n === 1 ? '' : 's'); }
  /* las marcas anteriores a la sincronizacion no tienen ts: cuentan desde su fecha */
  function tsDe(r) { return r ? (r.ts || Date.parse(r.f || '') || 0) : -1; }
  function activa(r) { return !!r && (r.e === 'leido' || r.e === 'leyendo'); }

  /* ── entorno y almacenes ───────────────────────────────────────────── */
  function conf() { return leerJSON(K_CONF, {}); }
  function entorno() { return conf().entorno || null; }
  function load() { var e = entorno(); return leerJSON(e ? K_LOCAL + ':' + e : K_LOCAL, {}); }
  function save(m) { var e = entorno(); return guardarJSON(e ? K_LOCAL + ':' + e : K_LOCAL, m); }
  function pendientes() { var e = entorno(); return e ? leerJSON('expedientes-pendientes:' + e, []) : []; }
  function guardarPendientes(p) { var e = entorno(); if (e) guardarJSON('expedientes-pendientes:' + e, p); }
  function marcarPendientes(ids) {
    if (!entorno() || !ids.length) return;
    var p = pendientes();
    ids.forEach(function (id) { if (p.indexOf(id) < 0) p.push(id); });
    guardarPendientes(p);
  }
  function cursor() { var e = entorno(); return e ? leerJSON('expedientes-cursor:' + e, 0) : 0; }
  function guardarCursor(c) { var e = entorno(); if (e) guardarJSON('expedientes-cursor:' + e, c); }
  function nuevoCodigo() {
    var b = new Uint8Array(20), s = '';
    crypto.getRandomValues(b);
    for (var i = 0; i < 20; i++) { s += ALFABETO[b[i] % 32]; if (i % 5 === 4 && i < 19) s += '-'; }
    return s;
  }
  function normalizarCodigo(s) {
    s = (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    return s.length === 20 ? s.replace(/(.{5})(?=.)/g, '$1-') : null;
  }

  var marks = load();
  var items = [].slice.call(document.querySelectorAll('article[data-id]'));

  /* que el navegador no borre las marcas por falta de espacio */
  try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e) {}

  /* contexto legible de una entrada, para el CSV */
  function ctx(a) {
    var sec = a.closest('section.bloque');
    var num = sec && sec.querySelector('.bloque-num');
    var tr = a.closest('.tramo');
    var trn = tr && tr.querySelector('.tramo-num');
    var h = a.querySelector('h3');
    return {
      b: num ? limpio(num.textContent) : '',
      tr: trn ? limpio(trn.textContent) : 'Evento',
      t: h ? limpio(h.textContent) : a.getAttribute('data-id')
    };
  }

  function toggle(a, estado) {
    var id = a.getAttribute('data-id'), c = ctx(a);
    marks = load();
    /* quitar una marca la deja como '' (no se borra) para que la retirada tambien llegue a los demas dispositivos */
    var e = marks[id] && marks[id].e === estado ? '' : estado;
    marks[id] = { e: e, ts: Date.now(), f: hoy(), x: EXP, b: c.b, tr: c.tr, t: c.t };
    save(marks);
    marcarPendientes([id]);
    render();
    programar(ESPERA_MS);
  }

  /* ── controles de cada entrada ─────────────────────────────────────── */
  items.forEach(function (a) {
    var box = document.createElement('div');
    box.className = 'lect';
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', 'Estado de lectura');
    [['leyendo', 'Leyendo'], ['leido', 'Leído']].forEach(function (s) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'lect-btn lect-' + s[0];
      b.setAttribute('data-estado', s[0]);
      b.setAttribute('aria-pressed', 'false');
      b.innerHTML = '<span class="lect-ico" aria-hidden="true"></span>' + s[1];
      b.addEventListener('click', function () { toggle(a, s[0]); });
      box.appendChild(b);
    });
    if (a.classList.contains('serie')) {
      var side = document.createElement('div');
      side.className = 'side';
      var tag = a.querySelector(':scope > .tag');
      if (tag) side.appendChild(tag);
      side.appendChild(box);
      a.appendChild(side);
    } else {
      box.classList.add('lect-ev');
      a.appendChild(box);
    }
  });

  /* ── panel ─────────────────────────────────────────────────────────── */
  var fab = document.createElement('button');
  fab.type = 'button';
  fab.className = 'lect-fab';
  fab.setAttribute('aria-expanded', 'false');
  fab.setAttribute('aria-controls', 'lect-panel');
  fab.innerHTML = '<span class="sync-dot" aria-hidden="true"></span>Lecturas <span class="fab-pct"></span>';

  var panel = document.createElement('div');
  panel.id = 'lect-panel';
  panel.className = 'lect-panel';
  panel.hidden = true;
  panel.innerHTML =
    '<p class="lp-title">Tus lecturas</p>' +
    '<p class="lp-res"></p>' +
    '<div class="lp-sync"></div>' +
    (items.length ? '<label class="lp-check"><input type="checkbox" id="lp-hide"> Ocultar lo ya leído</label>' : '') +
    '<div class="lp-actions"><button type="button" id="lp-exp">Exportar CSV</button>' +
    '<button type="button" id="lp-imp">Importar CSV</button>' +
    '<input type="file" id="lp-file" accept=".csv,text/csv" hidden></div>' +
    '<p class="lp-msg" role="status" aria-live="polite"></p>';
  document.body.appendChild(panel);
  document.body.appendChild(fab);

  function abrir(si) {
    panel.hidden = !si;
    fab.setAttribute('aria-expanded', si ? 'true' : 'false');
    if (si) pintarSync();
  }
  fab.addEventListener('click', function () { abrir(panel.hidden); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) { abrir(false); fab.focus(); }
  });
  document.addEventListener('click', function (e) {
    if (!panel.hidden && !panel.contains(e.target) && !fab.contains(e.target)) abrir(false);
  });

  var hide = panel.querySelector('#lp-hide');
  if (hide) {
    try { hide.checked = localStorage.getItem(K_HIDE) === '1'; } catch (e) {}
    document.documentElement.classList.toggle('ocultar-leidos', hide.checked);
    hide.addEventListener('change', function () {
      document.documentElement.classList.toggle('ocultar-leidos', hide.checked);
      try { localStorage.setItem(K_HIDE, hide.checked ? '1' : '0'); } catch (e) {}
    });
  }

  var msg = panel.querySelector('.lp-msg');
  function aviso(t) { msg.textContent = t; }

  /* ── sincronizacion ────────────────────────────────────────────────── */
  var estadoSync = 'local', detalleSync = '', ultimaSync = 0, enCurso = false, repetir = false, temporizador = null;

  function ErrorServicio(m) { this.message = m; }

  function programar(ms) {
    if (!entorno() || !URL_SERVICIO) return;
    clearTimeout(temporizador);
    temporizador = setTimeout(sincronizar, ms);
  }

  /* envia los cambios pendientes y recibe los de los demas dispositivos; gana el cambio mas reciente */
  function sincronizar() {
    var env = entorno();
    if (!env || !URL_SERVICIO) { estadoSync = 'local'; pintarSync(); return Promise.resolve(false); }
    if (enCurso) { repetir = true; return Promise.resolve(false); }
    clearTimeout(temporizador);
    enCurso = true;
    estadoSync = 'sincronizando'; pintarSync();
    var m = load(), cambios = {}, enviados = {};
    pendientes().forEach(function (id) {
      if (!m[id]) return;
      var r = Object.assign({}, m[id]);
      r.ts = tsDe(r);
      cambios[id] = r; enviados[id] = r.ts;
    });
    var control = window.AbortController ? new AbortController() : null;
    var corte = setTimeout(function () { if (control) control.abort(); }, TIEMPO_MS);
    /* text/plain: peticion "simple", sin consulta CORS previa */
    return fetch(URL_SERVICIO + '/v1/entornos/' + env + '/sincronizar', {
      method: 'POST', headers: { 'Content-Type': 'text/plain' }, cache: 'no-store',
      body: JSON.stringify({ cambios: cambios, desde: cursor() }), signal: control ? control.signal : undefined
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new ErrorServicio(d.error || 'el servicio respondió ' + r.status);
        return d;
      });
    }).then(function (d) {
      if (entorno() !== env) return false;               // se cambio de entorno mientras tanto
      var local = load(), hubo = false;
      Object.keys(d.marcas || {}).forEach(function (id) {
        var s = d.marcas[id];
        if (tsDe(s) > tsDe(local[id])) { local[id] = s; hubo = true; }
      });
      save(local);
      /* lo que se ha vuelto a cambiar durante el envio sigue pendiente */
      guardarPendientes(pendientes().filter(function (id) { return !(id in enviados) || tsDe(local[id]) !== enviados[id]; }));
      guardarCursor(d.cursor || 0);
      ultimaSync = Date.now(); detalleSync = '';
      estadoSync = 'ok';
      marks = local;
      render();
      return hubo;
    }).catch(function (e) {
      if (e instanceof ErrorServicio) { estadoSync = 'error'; detalleSync = e.message; }
      else { estadoSync = 'sin-conexion'; detalleSync = ''; }
      pintarSync();
      return false;
    }).then(function (v) {
      clearTimeout(corte);
      enCurso = false;
      if (repetir || (estadoSync === 'ok' && pendientes().length)) { repetir = false; programar(300); }
      return v;
    });
  }

  function entrarEnEntorno(codigo, subirLocales) {
    var c = conf(); c.entorno = codigo; guardarJSON(K_CONF, c);
    var m = load(), ids = [];
    if (subirLocales) {
      var loc = leerJSON(K_LOCAL, {});
      Object.keys(loc).forEach(function (id) {
        if (tsDe(loc[id]) > tsDe(m[id])) { m[id] = Object.assign({}, loc[id], { ts: tsDe(loc[id]) }); ids.push(id); }
      });
      save(m);
    }
    marcarPendientes(ids);
    estadoSync = 'sincronizando';
    marks = load();
    render();
    return sincronizar();
  }

  function salirDelEntorno() {
    var env = entorno();
    if (!env) return;
    /* el dispositivo se queda con una copia de lo ultimo que sabia */
    var m = load(), loc = leerJSON(K_LOCAL, {});
    Object.keys(m).forEach(function (id) { if (tsDe(m[id]) > tsDe(loc[id])) loc[id] = m[id]; });
    guardarJSON(K_LOCAL, loc);
    var c = conf(); delete c.entorno; guardarJSON(K_CONF, c);
    clearTimeout(temporizador);
    estadoSync = 'local';
    marks = load();
    render();
  }

  function cuantasLocales() {
    var loc = leerJSON(K_LOCAL, {}), n = 0;
    for (var k in loc) if (activa(loc[k])) n++;
    return n;
  }

  function hace(ms) {
    var s = Math.round((Date.now() - ms) / 1000);
    if (s < 45) return 'hace un momento';
    if (s < 3600) return 'hace ' + Math.max(1, Math.round(s / 60)) + ' min';
    return 'hace ' + Math.round(s / 3600) + ' h';
  }

  var TITULOS = {
    local: 'Marcas guardadas solo en este dispositivo', ok: 'Sincronizado', pendiente: 'Cambios pendientes de enviar',
    sincronizando: 'Sincronizando', 'sin-conexion': 'Sin conexión: se enviará al recuperarla', error: 'Error de sincronización'
  };
  var pintado = '';

  function pintarSync() {
    var env = entorno(), p = pendientes().length;
    var clase = !env || !URL_SERVICIO ? 'local' : (estadoSync === 'ok' && p ? 'pendiente' : estadoSync);
    fab.querySelector('.sync-dot').className = 'sync-dot s-' + clase;
    fab.title = TITULOS[clase] || '';
    if (panel.hidden) return;

    var h;
    if (!URL_SERVICIO) {
      h = '<p class="sy-estado">Las marcas se guardan solas en este navegador y las comparten todos los expedientes. ' +
          'Exporta el CSV de vez en cuando como copia: si cambias de navegador o borras sus datos, impórtalo y lo recuperas todo.</p>';
    } else if (!env) {
      h = '<p class="sy-estado s-local">Tus marcas solo están en este dispositivo.</p>' +
          '<p class="lp-note">Con un <strong>entorno</strong> se guardan también en línea: las ves en el PC, el móvil y la tablet, ' +
          'y no se pierden si se borran los datos del navegador. Sin conexión siguen funcionando igual.</p>' +
          '<div class="lp-actions"><button type="button" id="sy-crear">Crear mi entorno</button>' +
          '<button type="button" id="sy-usar">Ya tengo un código</button></div>' +
          '<div class="sy-unirse" hidden><label for="sy-codigo">Código del entorno</label>' +
          '<input id="sy-codigo" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="xxxxx-xxxxx-xxxxx-xxxxx">' +
          '<div class="lp-actions"><button type="button" id="sy-entrar">Conectar</button></div></div>';
    } else {
      var linea = {
        ok: 'Sincronizado ' + hace(ultimaSync) + '.',
        pendiente: plural(p, 'cambio') + ' pendiente' + (p === 1 ? '' : 's') + ' de enviar.',
        sincronizando: 'Sincronizando…',
        'sin-conexion': 'Sin conexión. Tus marcas se guardan en este dispositivo' +
                        (p ? ' (' + plural(p, 'cambio') + ' pendiente' + (p === 1 ? '' : 's') + ')' : '') + ' y se enviarán al recuperarla.',
        error: 'No se pudo sincronizar: ' + esc(detalleSync) + '.'
      }[clase] || '';
      h = '<p class="sy-estado s-' + clase + '">' + linea + '</p>' +
          '<p class="sy-lbl">Tu entorno</p><p class="sy-codigo"><code>' + env + '</code></p>' +
          '<div class="lp-actions"><button type="button" id="sy-ahora">Sincronizar ahora</button>' +
          '<button type="button" id="sy-copiar">Copiar código</button>' +
          '<button type="button" id="sy-salir">Desconectar</button></div>' +
          '<p class="lp-note">En otro dispositivo, abre cualquier expediente, pulsa «Lecturas» → «Ya tengo un código» y escribe este. ' +
          'Guárdalo bien: es la llave de tus lecturas.</p>';
    }
    if (h === pintado) return;            // no rehacer el panel (ni perder lo que se esta escribiendo) si no cambia
    pintado = h;
    var box = panel.querySelector('.lp-sync');
    box.innerHTML = h;
    var q = function (id) { return box.querySelector('#' + id); };

    if (q('sy-crear')) q('sy-crear').onclick = function () {
      var n = cuantasLocales();
      var subir = n ? confirm('Tienes ' + plural(n, 'marca') + ' en este dispositivo. ¿Las guardo en tu nuevo entorno?') : false;
      entrarEnEntorno(nuevoCodigo(), subir).then(function () {
        aviso(estadoSync === 'ok' ? 'Entorno creado. Copia el código y úsalo en tus otros dispositivos.'
                                  : 'Entorno creado. Se guardará en línea en cuanto haya conexión.');
      });
    };
    if (q('sy-usar')) q('sy-usar').onclick = function () { box.querySelector('.sy-unirse').hidden = false; q('sy-codigo').focus(); };
    if (q('sy-codigo')) q('sy-codigo').onkeydown = function (e) { if (e.key === 'Enter') q('sy-entrar').click(); };
    if (q('sy-entrar')) q('sy-entrar').onclick = function () {
      var cod = normalizarCodigo(q('sy-codigo').value);
      if (!cod) { aviso('El código tiene 20 letras y números (los guiones son opcionales). Revísalo.'); return; }
      var n = cuantasLocales();
      var subir = n ? confirm('Tienes ' + plural(n, 'marca') + ' en este dispositivo. ¿Las añado también a este entorno?') : false;
      entrarEnEntorno(cod, subir).then(function () {
        aviso(estadoSync === 'ok' ? 'Conectado: tu progreso ya está en este dispositivo.'
                                  : 'Código guardado. Se sincronizará en cuanto haya conexión.');
      });
    };
    if (q('sy-ahora')) q('sy-ahora').onclick = function () { sincronizar(); };
    if (q('sy-copiar')) q('sy-copiar').onclick = function () {
      var mal = function () { aviso('No se pudo copiar: selecciona el código y cópialo a mano.'); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(env).then(function () { aviso('Código copiado.'); }, mal);
      else mal();
    };
    if (q('sy-salir')) q('sy-salir').onclick = function () {
      if (!confirm('Este dispositivo dejará de sincronizarse. Tu progreso sigue guardado en el entorno y aquí se queda una copia. ¿Desconectar?')) return;
      salirDelEntorno();
      aviso('Desconectado. Para volver, usa otra vez tu código.');
    };
  }

  /* ── CSV ───────────────────────────────────────────────────────────── */
  function campo(v) {
    v = String(v == null ? '' : v);
    return /[";\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  }
  function exportCSV() {
    var m = load(), filas = [['expediente', 'bloque', 'tramo', 'entrada', 'estado', 'fecha', 'id']];
    Object.keys(m).sort().forEach(function (id) {
      var r = m[id];
      if (!activa(r)) return;
      filas.push([NOMBRES[r.x] || r.x || '', r.b || '', r.tr || '', r.t || '',
                  r.e === 'leido' ? 'Leído' : 'Leyendo', r.f || '', id]);
    });
    return '﻿' + filas.map(function (f) { return f.map(campo).join(';'); }).join('\r\n') + '\r\n';
  }
  function parseCSV(t) {
    t = t.replace(/^﻿/, '');
    var primera = t.split(/\r?\n/)[0] || '';
    var sep = primera.indexOf(';') >= 0 ? ';' : ',';
    var filas = [], fila = [], c = '', q = false;
    for (var i = 0; i < t.length; i++) {
      var ch = t[i];
      if (q) {
        if (ch === '"') { if (t[i + 1] === '"') { c += '"'; i++; } else q = false; }
        else c += ch;
      } else if (ch === '"') q = true;
      else if (ch === sep) { fila.push(c); c = ''; }
      else if (ch === '\n') { fila.push(c); filas.push(fila); fila = []; c = ''; }
      else if (ch !== '\r') c += ch;
    }
    if (c !== '' || fila.length) { fila.push(c); filas.push(fila); }
    return filas;
  }
  function importCSV(t) {
    var filas = parseCSV(t);
    if (!filas.length) return { n: 0, err: 'El archivo está vacío.' };
    var h = filas[0].map(function (s) { return limpio(s).toLowerCase(); });
    var col = function (n) { return h.indexOf(n); };
    var iId = col('id'), iE = col('estado'), iF = col('fecha'), iX = col('expediente'),
        iB = col('bloque'), iT = col('tramo'), iN = col('entrada');
    if (iId < 0 || iE < 0) return { n: 0, err: 'No es un CSV de lecturas: faltan las columnas «id» y «estado».' };
    var inv = {}; for (var k in NOMBRES) inv[NOMBRES[k]] = k;
    var m = load(), ids = [], ahora = Date.now();
    filas.slice(1).forEach(function (r) {
      var id = limpio(r[iId]);
      if (!id) return;
      var est = limpio(r[iE]).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      var e = est === 'leido' ? 'leido' : (est === 'leyendo' ? 'leyendo' : '');
      if (!e) return;
      m[id] = {
        e: e, ts: ahora, f: (iF >= 0 && limpio(r[iF])) || hoy(),
        x: (iX >= 0 && inv[limpio(r[iX])]) || ubicacion(id).split('-')[0],
        b: iB >= 0 ? limpio(r[iB]) : '', tr: iT >= 0 ? limpio(r[iT]) : '', t: iN >= 0 ? limpio(r[iN]) : ''
      };
      ids.push(id);
    });
    save(m);
    marcarPendientes(ids);
    programar(ESPERA_MS);
    return { n: ids.length };
  }

  panel.querySelector('#lp-exp').addEventListener('click', function () {
    var blob = new Blob([exportCSV()], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'expedientes-leidos-' + hoy() + '.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    var m = load(), n = 0;
    for (var k in m) if (activa(m[k])) n++;
    aviso('CSV exportado con ' + plural(n, 'marca') + '. Lo encontrarás en Descargas.');
  });
  var file = panel.querySelector('#lp-file');
  panel.querySelector('#lp-imp').addEventListener('click', function () { file.click(); });
  file.addEventListener('change', function () {
    var f = file.files && file.files[0];
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var r = importCSV(String(rd.result));
      marks = load(); render();
      aviso(r.err ? r.err : 'Importadas ' + r.n + ' marcas. Las que ya tenías se conservan; las del CSV mandan si coinciden.');
      file.value = '';
    };
    rd.onerror = function () { aviso('No se pudo leer el archivo. Prueba a exportarlo de nuevo.'); };
    rd.readAsText(f, 'utf-8');
  });

  /* ── pintar estado y progreso ──────────────────────────────────────── */
  function render() {
    var leidos = 0, leyendo = 0;
    items.forEach(function (a) {
      var m = marks[a.getAttribute('data-id')], e = activa(m) ? m.e : '';
      a.classList.toggle('st-leido', e === 'leido');
      a.classList.toggle('st-leyendo', e === 'leyendo');
      [].forEach.call(a.querySelectorAll('.lect-btn'), function (b) {
        var on = b.getAttribute('data-estado') === e;
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.title = on ? 'Quitar la marca' : '';
      });
      if (e === 'leido') leidos++; else if (e === 'leyendo') leyendo++;
    });

    if (items.length) {
      [].forEach.call(document.querySelectorAll('section.bloque'), function (sec) {
        var its = sec.querySelectorAll('article[data-id]'), n = its.length, r = 0, l = 0;
        if (!n) return;
        [].forEach.call(its, function (a) {
          var m = marks[a.getAttribute('data-id')];
          if (!activa(m)) return;
          if (m.e === 'leido') r++; else l++;
        });
        var p = sec.querySelector('.prog-bloque');
        if (!p) { p = document.createElement('div'); p.className = 'prog-bloque'; sec.querySelector('.bloque-head').appendChild(p); }
        p.innerHTML = bar(r, n) + '<span>' + texto(r, n, l) + '</span>';
        var link = document.querySelector('nav.spine a[href="#' + sec.id + '"]');
        if (link) {
          var s = link.querySelector('.nav-prog');
          if (!s) { s = document.createElement('span'); s.className = 'nav-prog'; link.appendChild(s); }
          s.textContent = r + '/' + n + (r === n ? ' ✓' : '');
          s.classList.toggle('done', r === n);
        }
      });
      var g = document.getElementById('prog-global');
      var st = document.querySelector('header.top .stats');
      if (!g && st) { g = document.createElement('div'); g.id = 'prog-global'; g.className = 'prog-global'; st.parentNode.insertBefore(g, st.nextSibling); }
      if (g) g.innerHTML = '<span class="pg-lbl">Tu progreso</span>' + bar(leidos, items.length) + '<span class="pg-txt">' + texto(leidos, items.length, leyendo) + '</span>';
    }

    /* elementos con progreso calculado por prefijo (pagina principal) */
    [].forEach.call(document.querySelectorAll('[data-prog][data-total]'), function (el) {
      var pre = el.getAttribute('data-prog'), n = +el.getAttribute('data-total'), r = 0, l = 0;
      for (var id in marks) {
        if (pre && ubicacion(id).indexOf(pre + '-') !== 0) continue;
        if (!activa(marks[id])) continue;
        if (marks[id].e === 'leido') r++; else l++;
      }
      r = Math.min(r, n);
      if (el.classList.contains('bar')) {
        el.style.setProperty('--p', pct(r, n) + '%');
        if (!el.hasAttribute('data-title')) el.setAttribute('data-title', el.title);
        el.title = el.getAttribute('data-title') + ' · ' + r + '/' + n + ' leídas';
      } else {
        el.innerHTML = (el.classList.contains('prog-global') ? '<span class="pg-lbl">Tu progreso</span>' : '') +
                       bar(r, n) + '<span class="pg-txt">' + texto(r, n, l) + '</span>';
      }
    });

    var todos = 0, curso = 0;
    for (var k in marks) { if (!activa(marks[k])) continue; if (marks[k].e === 'leido') todos++; else curso++; }
    var res = items.length ? 'En este expediente: ' + texto(leidos, items.length, leyendo) + '. ' : '';
    panel.querySelector('.lp-res').textContent = res + 'En toda la colección: ' + todos + ' leídas' + (curso ? ', ' + curso + ' en curso' : '') + '.';
    fab.querySelector('.fab-pct').textContent = items.length ? pct(leidos, items.length) + '%' : todos + ' leídas';
    pintarSync();
  }

  /* ── arranque y momentos en que se sincroniza ──────────────────────── */
  window.addEventListener('storage', function (e) {      // otra pestaña de la coleccion cambio algo
    if (e.key && e.key.indexOf('expedientes-') === 0) { marks = load(); render(); }
  });
  window.addEventListener('online', function () { sincronizar(); });
  window.addEventListener('offline', function () { if (entorno() && URL_SERVICIO) { estadoSync = 'sin-conexion'; pintarSync(); } });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && Date.now() - ultimaSync > 30000) sincronizar();
  });
  setInterval(function () {
    if (document.visibilityState === 'visible') sincronizar(); else pintarSync();
  }, CADA_MS);

  if (entorno() && URL_SERVICIO) estadoSync = pendientes().length ? 'pendiente' : 'sincronizando';
  render();
  if (entorno() && URL_SERVICIO) sincronizar();

  window.ExpedientesLecturas = {
    exportCSV: exportCSV,
    importCSV: function (t) { var r = importCSV(t); marks = load(); render(); return r; },
    crearEntorno: function (subir) { return entrarEnEntorno(nuevoCodigo(), !!subir).then(entorno); },
    usarEntorno: function (codigo, subir) {
      var c = normalizarCodigo(codigo);
      return c ? entrarEnEntorno(c, !!subir) : Promise.reject(new Error('código no válido'));
    },
    desconectar: salirDelEntorno,
    sincronizar: sincronizar,
    estado: function () {
      var m = load(), n = 0;
      for (var k in m) if (activa(m[k])) n++;
      return { entorno: entorno(), estado: estadoSync, pendientes: pendientes().length, marcas: n, servicio: URL_SERVICIO };
    }
  };
})();
