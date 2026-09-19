import crypto from 'node:crypto';

const ATTR_KEYS = [
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_id', 'utm_content', 'utm_term',
  'campaign_id', 'gclid', 'gbraid', 'wbraid', 'fbclid', 'ttclid', 'adset_id', 'ad_id', 'placement'
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

function inferFromReferrer(referrer = '') {
  if (!referrer) return {};
  try {
    const host = new URL(referrer).hostname.toLowerCase();
    if (host.includes('instagram.com')) return { utm_source: 'instagram', utm_medium: 'organic_social' };
    if (host.includes('facebook.com') || host.includes('fb.com')) return { utm_source: 'facebook', utm_medium: 'organic_social' };
    if (host.includes('threads.net')) return { utm_source: 'threads', utm_medium: 'organic_social' };
    if (host.includes('tiktok.com')) return { utm_source: 'tiktok', utm_medium: 'organic_social' };
    if (host.includes('google.')) return { utm_source: 'google', utm_medium: 'organic' };
    return { utm_source: host.replace(/^www\./, ''), utm_medium: 'referral' };
  } catch {
    return {};
  }
}

export function extractAttribution(url, referrer = '') {
  const out = {};
  for (const key of ATTR_KEYS) {
    const value = url.searchParams.get(key);
    if (value) out[key] = value.slice(0, 500);
  }
  if (referrer) out.referrer = referrer.slice(0, 1000);

  if (!out.utm_source) {
    if (out.gclid || out.gbraid || out.wbraid) {
      out.utm_source = 'google';
      out.utm_medium = out.utm_medium || 'cpc';
    } else if (out.ttclid) {
      out.utm_source = 'tiktok';
      out.utm_medium = out.utm_medium || 'paid_social';
    } else if (out.fbclid) {
      out.utm_source = 'meta';
      out.utm_medium = out.utm_medium || ((out.ad_id || out.adset_id) ? 'paid_social' : 'referral');
    } else {
      Object.assign(out, inferFromReferrer(referrer));
    }
  }

  return out;
}

export function attributionPlatform(attr = {}) {
  const source = String(attr.utm_source || '').toLowerCase();
  if (attr.gclid || attr.gbraid || attr.wbraid || source === 'google') return 'google';
  if (attr.fbclid || ['meta', 'facebook', 'instagram'].includes(source)) return source === 'instagram' ? 'instagram' : 'meta';
  if (attr.ttclid || source === 'tiktok') return 'tiktok';
  return source || 'direct';
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

export function cookie(name, value, { maxAge = 60 * 60 * 24 * 365, secure = true, sameSite = 'Lax', domain = '' } = {}) {
  return `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=${sameSite}${domain ? `; Domain=${domain}` : ''}${secure ? '; Secure' : ''}`;
}
