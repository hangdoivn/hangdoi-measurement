import crypto from 'node:crypto';

const ATTR_KEYS = [
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_id', 'utm_content', 'utm_term',
  'gclid', 'gbraid', 'wbraid', 'fbclid', 'ttclid', 'adset_id', 'ad_id', 'placement'
];

export function parseCookies(header = '') {
  return Object.fromEntries(header.split(';').map(v => v.trim()).filter(Boolean).map(pair => {
    const idx = pair.indexOf('=');
    return idx < 0 ? [pair, ''] : [pair.slice(0, idx), decodeURIComponent(pair.slice(idx + 1))];
  }));
}

export function makeId(prefix) {
  return `${prefix}_${crypto.randomUUID()}`;
}

export function extractAttribution(url, referrer = '') {
  const out = {};
  for (const key of ATTR_KEYS) {
    const value = url.searchParams.get(key);
    if (value) out[key] = value.slice(0, 500);
  }
  if (referrer) out.referrer = referrer.slice(0, 1000);
  return out;
}

export function encodeAttribution(attr) {
  return Buffer.from(JSON.stringify(attr || {}), 'utf8').toString('base64url');
}

export function decodeAttribution(value) {
  if (!value) return {};
  try { return JSON.parse(Buffer.from(value, 'base64url').toString('utf8')); }
  catch { return {}; }
}

export function classifyDevice(userAgent = '') {
  const ua = userAgent.toLowerCase();
  if (/ipad|tablet/.test(ua)) return 'tablet';
  if (/mobi|android|iphone|ipod/.test(ua)) return 'mobile';
  return 'desktop';
}

export function isLikelyBot(userAgent = '') {
  return /bot|crawler|spider|slurp|headless|lighthouse|pagespeed/i.test(userAgent);
}

export function cookie(name, value, { maxAge = 60 * 60 * 24 * 365, secure = true, sameSite = 'Lax' } = {}) {
  return `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=${sameSite}${secure ? '; Secure' : ''}`;
}
