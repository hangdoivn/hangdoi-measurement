import { isIP } from 'node:net';

let reader = null;
let status = 'not_initialized';

function normalizeIp(value = '') {
  let ip = String(value || '').trim();
  if (!ip) return '';
  if (ip.startsWith('::ffff:')) ip = ip.slice(7);
  if (ip.includes('%')) ip = ip.split('%')[0];
  return isIP(ip) ? ip : '';
}

function isPrivateIp(ip) {
  if (!ip) return true;
  if (ip === '127.0.0.1' || ip === '::1') return true;
  if (/^10\./.test(ip) || /^192\.168\./.test(ip)) return true;
  const m = ip.match(/^172\.(\d+)\./);
  if (m && Number(m[1]) >= 16 && Number(m[1]) <= 31) return true;
  return /^fc|^fd|^fe80:/i.test(ip);
}

export function clientIp(req) {
  // Nginx overwrites X-Real-IP with the directly connected client address,
  // making it preferable to a user-supplied X-Forwarded-For chain.
  const real = normalizeIp(req.headers['x-real-ip']);
  if (real) return real;

  const forwarded = String(req.headers['x-forwarded-for'] || '')
    .split(',')
    .map(v => normalizeIp(v))
    .filter(Boolean);
  if (forwarded.length) return forwarded[forwarded.length - 1];

  return normalizeIp(req.socket?.remoteAddress || '');
}

export async function initGeo() {
  try {
    const maxmindModule = await import('maxmind');
    const geolite = await import('geolite2-redist');
    const maxmind = maxmindModule.default || maxmindModule;
    reader = await geolite.open('GeoLite2-City', dbPath => maxmind.open(dbPath));
    status = 'ready';
  } catch (error) {
    reader = null;
    status = 'unavailable';
    console.error('GeoIP initialization failed; tracking continues without geo:', error?.message || error);
  }
  return status;
}

export function geoStatus() {
  return status;
}

export function coarseGeo(req) {
  if (!reader) return {};
  const ip = clientIp(req);
  if (!ip || isPrivateIp(ip)) return {};

  try {
    const row = reader.get(ip);
    if (!row) return {};

    const subdivision = Array.isArray(row.subdivisions) ? row.subdivisions[0] : null;
    const geo = {
      countryCode: row.country?.iso_code || row.registered_country?.iso_code || undefined,
      country: row.country?.names?.en || row.registered_country?.names?.en || undefined,
      regionCode: subdivision?.iso_code || undefined,
      region: subdivision?.names?.en || undefined,
      city: row.city?.names?.en || undefined,
      timezone: row.location?.time_zone || undefined,
    };

    return Object.fromEntries(Object.entries(geo).filter(([, value]) => Boolean(value)));
  } catch {
    return {};
  }
}
