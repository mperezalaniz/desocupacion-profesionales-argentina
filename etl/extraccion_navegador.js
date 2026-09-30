/*
 * Extracción usada en este proyecto (transparencia metodológica).
 * Se ejecutó en la consola del navegador sobre https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos
 * porque el entorno de cómputo no tenía acceso directo al sitio del INDEC.
 * Lee cada zip EPH_usu_XTrim_AAAA_txt.zip, descomprime usu_individual y agrega por celdas:
 *   __A: periodo|region|gran_mendoza|nivel_ed|tipo_titulo|grupo_edad|estado -> [Σw, Σw², n]
 *   __B (solo ocupados): periodo|gran_mendoza|grupo_ed|calificacion|asalariado|pp07h|intensi -> [Σw, Σw², n]
 * De esas celdas se derivan todas las tasas de data/eph_resultados.csv.
 * El equivalente reproducible en Python/SQL es etl/procesar_eph.py + sql/02_indicadores_desde_microdatos.sql.
 */
window.__A = window.__A || {};
window.__B = window.__B || {};

// Lector de zip mínimo (directorio central + DecompressionStream), sin librerías externas
window.__unzip = async function (buf) {
  const dv = new DataView(buf); const u8 = new Uint8Array(buf);
  let e = buf.byteLength - 22; while (e > 0 && dv.getUint32(e, true) !== 0x06054b50) e--;
  const cnt = dv.getUint16(e + 10, true); let p = dv.getUint32(e + 16, true); const out = {};
  for (let i = 0; i < cnt; i++) {
    const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true), nlen = dv.getUint16(p + 28, true),
      xlen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true), loff = dv.getUint32(p + 42, true);
    const name = new TextDecoder().decode(u8.slice(p + 46, p + 46 + nlen));
    out[name] = { method, csize, loff }; p += 46 + nlen + xlen + clen;
  }
  return out;
};

window.__read = async function (buf, ent) {
  const dv = new DataView(buf); const lo = ent.loff;
  const nlen = dv.getUint16(lo + 26, true), xlen = dv.getUint16(lo + 28, true);
  const data = new Uint8Array(buf, lo + 30 + nlen + xlen, ent.csize);
  let bytes;
  if (ent.method === 0) bytes = data;
  else {
    const s = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    bytes = new Uint8Array(await new Response(s).arrayBuffer());
  }
  return new TextDecoder('latin1').decode(bytes);
};

window.__proc = async function (url) {
  const ageBin = a => a < 25 ? '15-24' : (a < 45 ? '25-44' : (a < 65 ? '45-64' : '65+'));
  const buf = await (await fetch(url)).arrayBuffer();
  const ents = await window.__unzip(buf);
  const f = Object.keys(ents).find(n => /personas|individual/i.test(n));
  const txt = await window.__read(buf, ents[f]);
  const lines = txt.split(/\r?\n/);
  const sep = lines[0].includes(';') ? ';' : ',';
  const H = lines[0].split(sep).map(s => s.replace(/"/g, '').trim().toUpperCase());
  const ix = {}; H.forEach((h, i) => ix[h] = i);
  let n = 0, q = null;
  for (let i = 1; i < lines.length; i++) {
    const L = lines[i]; if (!L) continue;
    const c = L.split(sep).map(s => s.replace(/"/g, '').trim());
    const est = +c[ix.ESTADO]; if (est !== 1 && est !== 2) continue;           // solo activos
    const w = +String(c[ix.PONDERA]).replace(',', '.'); if (!(w > 0)) continue;
    q = c[ix.ANO4] + 'Q' + c[ix.TRIMESTRE];
    const reg = c[ix.REGION], gm = (+c[ix.AGLOMERADO] === 10) ? 1 : 0;
    const niv = +c[ix.NIVEL_ED] || 9, ch12 = +c[ix.CH12];
    const det = niv === 6 ? (ch12 === 6 ? 'terciario' : (ch12 === 8 ? 'posgrado' : (ch12 === 7 ? 'universitario' : 'otro'))) : '-';
    const kA = [q, reg, gm, niv, det, ageBin(+c[ix.CH06]), est].join('|');
    const a = window.__A[kA] || (window.__A[kA] = [0, 0, 0]); a[0] += w; a[1] += w * w; a[2] += 1;
    if (est === 1) {
      const ng = niv === 6 ? 'sup_completo' : (niv === 5 ? 'sup_incompleto' : (niv === 4 ? 'sec_completo' : 'menos_sec'));
      // CNO: calificación = 5° dígito, completando ceros a la izquierda perdidos
      const raw = String(c[ix.PP04D_COD] || '').replace(/\D/g, '');
      const cal = (raw.length >= 3 && raw.length <= 5) ? raw.padStart(5, '0')[4] : '0';
      const asal = +c[ix.CAT_OCUP] === 3 ? 1 : 0; const p7 = asal ? (+c[ix.PP07H] || 0) : 0;
      const kB = [q, gm, ng, cal, asal, p7, +c[ix.INTENSI] || 0].join('|');
      const b = window.__B[kB] || (window.__B[kB] = [0, 0, 0]); b[0] += w; b[1] += w * w; b[2] += 1;
    }
    n++;
  }
  return q + ' n=' + n;
};
