// Servicio de lecturas de Expedientes Marvel (Cloudflare Worker + base de datos D1 enlazada como "DB").
//
//   GET  /v1/salud                              -> { ok, version }
//   POST /v1/entornos/{codigo}/sincronizar      cuerpo: { cambios: { id: marca }, desde: cursor }
//                                               -> { marcas: { id: marca }, cursor }
//
// Cada marca es { e: 'leido' | 'leyendo' | '', ts: ms, f, x, b, tr, t }. Para cada entrada gana la de
// "ts" mas reciente; la comparacion la hace la propia base de datos en una sola sentencia, asi que
// dos dispositivos sincronizando a la vez no se pisan. El servicio devuelve solo lo que ha cambiado
// desde el "cursor" que el dispositivo recibio en su sincronizacion anterior.
//
// La replica para pruebas locales es servidor_local.py: si cambias algo aqui, cambialo tambien alli.

const VERSION = 1;
const MAX_CUERPO = 512 * 1024;     // bytes por peticion
const MAX_CAMBIOS = 3000;          // marcas por peticion
const SOLAPE_MS = 5000;            // el cursor va 5 s por detras: lo repetido se ignora, lo concurrente no se pierde
const RE_ENTORNO = /^[a-z0-9]{5}(-[a-z0-9]{5}){3}$/;
const RE_ID = /^[a-z0-9][a-z0-9-]{0,150}$/;
const ESTADOS = new Set(['leido', 'leyendo', '']);
const CAMPOS = ['f', 'x', 'b', 'tr', 't'];

const UPSERT =
  'INSERT INTO marcas (entorno, id, estado, ts, datos, actualizado) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ' +
  'ON CONFLICT (entorno, id) DO UPDATE SET estado = excluded.estado, ts = excluded.ts, ' +
  'datos = excluded.datos, actualizado = excluded.actualizado WHERE excluded.ts > marcas.ts';
const CAMBIADAS = 'SELECT id, estado, ts, datos FROM marcas WHERE entorno = ?1 AND actualizado > ?2';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

function respuesta(obj, estado = 200) {
  return new Response(JSON.stringify(obj), {
    status: estado,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...CORS },
  });
}

function datosDe(marca) {
  const d = {};
  for (const k of CAMPOS) if (typeof marca[k] === 'string') d[k] = marca[k].slice(0, 300);
  return JSON.stringify(d);
}

export default {
  async fetch(peticion, env) {
    if (peticion.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    const url = new URL(peticion.url);
    if (url.pathname === '/v1/salud') return respuesta({ ok: true, version: VERSION });

    const ruta = url.pathname.match(/^\/v1\/entornos\/([^/]+)\/sincronizar$/);
    if (!ruta || peticion.method !== 'POST') return respuesta({ error: 'Ruta no encontrada' }, 404);
    const entorno = ruta[1];
    if (!RE_ENTORNO.test(entorno)) return respuesta({ error: 'Código de entorno no válido' }, 400);

    const texto = await peticion.text();
    if (texto.length > MAX_CUERPO) return respuesta({ error: 'Petición demasiado grande' }, 413);
    let cuerpo;
    try { cuerpo = JSON.parse(texto || '{}'); } catch { return respuesta({ error: 'JSON no válido' }, 400); }
    const cambios = cuerpo && typeof cuerpo.cambios === 'object' && cuerpo.cambios ? cuerpo.cambios : {};
    const ids = Object.keys(cambios);
    if (ids.length > MAX_CAMBIOS) return respuesta({ error: 'Demasiados cambios en una petición' }, 413);
    const desde = Number.isFinite(cuerpo.desde) ? cuerpo.desde : 0;

    const ahora = Date.now();
    const sentencias = [];
    for (const id of ids) {
      const m = cambios[id];
      if (!RE_ID.test(id) || !m || !ESTADOS.has(m.e) || !Number.isFinite(m.ts)) continue;
      sentencias.push(env.DB.prepare(UPSERT).bind(entorno, id, m.e, Math.floor(m.ts), datosDe(m), ahora));
    }
    if (sentencias.length) await env.DB.batch(sentencias);

    const { results } = await env.DB.prepare(CAMBIADAS).bind(entorno, desde).all();
    const marcas = {};
    for (const f of results) marcas[f.id] = { e: f.estado, ts: f.ts, ...JSON.parse(f.datos) };
    return respuesta({ marcas, cursor: ahora - SOLAPE_MS });
  },
};
