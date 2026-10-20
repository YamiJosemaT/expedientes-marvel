-- Servicio de lecturas de Expedientes Marvel: una fila por marca y por entorno.
-- El mismo esquema sirve para Cloudflare D1 (en la nube) y para servidor_local.py (pruebas).

CREATE TABLE IF NOT EXISTS marcas (
  entorno     TEXT    NOT NULL,   -- codigo del entorno de una persona (xxxxx-xxxxx-xxxxx-xxxxx)
  id          TEXT    NOT NULL,   -- id de la entrada del expediente (m1-b4-uncanny-x-men-500-512)
  estado      TEXT    NOT NULL,   -- 'leido', 'leyendo' o '' (marca quitada)
  ts          INTEGER NOT NULL,   -- momento del cambio en el dispositivo (ms): gana el mas reciente
  datos       TEXT    NOT NULL,   -- JSON con fecha, expediente, bloque, tramo y titulo (para el CSV)
  actualizado INTEGER NOT NULL,   -- momento en que lo recibio el servicio (ms): para enviar solo lo nuevo
  PRIMARY KEY (entorno, id)
);

CREATE INDEX IF NOT EXISTS marcas_por_actualizacion ON marcas (entorno, actualizado);
