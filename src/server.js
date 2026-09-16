import http from 'node:http';
import { config } from './config.js';
import { akimitsu } from './projects/akimitsu.js';
import { recordEvent, eventSummary, migrate, dbMode } from './db.js';
import {
  parseCookies, makeId, extractAttribution, encodeAttribution, decodeAttribution,
  classifyDevice, isLikelyBot, cookie
} from './attribution.js';

const WORKSPACE_ID = 'hangdoi';

function send(res, status, body, type = 'text/plain; charset=utf-8', headers = {}) {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store', ...headers });
  res.end(body);
}

function json(res, status, value) { send(res, status, JSON.stringify(value), 'application/json; charset=utf-8'); }

function clientContext(req, url) {
  const cookies = parseCookies(req.headers.cookie || '');
  const now = Date.now();
  const visitorId = cookies.hd_vid || makeId('v');
  const last = Number(cookies.hd_last || 0);
  const stale = !last || now - last > config.sessionTtlMinutes * 60_000;
  const sessionId = stale ? makeId('s') : (cookies.hd_sid || makeId('s'));
  const incomingAttr = extractAttribution(url, req.headers.referer || '');
  const storedFirstTouch = decodeAttribution(cookies.hd_ft);
  const storedLastTouch = decodeAttribution(cookies.hd_lt);
  const hasIncomingCampaignSignal = Object.keys(incomingAttr).some(key => key !== 'referrer');
  const firstTouch = Object.keys(storedFirstTouch).length ? storedFirstTouch : (hasIncomingCampaignSignal ? incomingAttr : {});
  const lastTouch = hasIncomingCampaignSignal ? incomingAttr : storedLastTouch;
  const setCookies = [
    cookie('hd_vid', visitorId, { secure: config.cookieSecure }),
    cookie('hd_sid', sessionId, { secure: config.cookieSecure, maxAge: config.sessionTtlMinutes * 60 }),
    cookie('hd_last', String(now), { secure: config.cookieSecure, maxAge: config.sessionTtlMinutes * 60 }),
    cookie('hd_ft', encodeAttribution(firstTouch), { secure: config.cookieSecure, maxAge: 60 * 60 * 24 * 90 }),
    cookie('hd_lt', encodeAttribution(lastTouch), { secure: config.cookieSecure, maxAge: 60 * 60 * 24 * 30 }),
  ];
  return { visitorId, sessionId, firstTouch, lastTouch, setCookies };
}

function toEvent(req, url, ctx, eventName, extra = {}) {
  return {
    eventId: makeId('evt'), workspaceId: WORKSPACE_ID, projectId: akimitsu.id,
    visitorId: ctx.visitorId, sessionId: ctx.sessionId, eventName,
    destinationKey: extra.destinationKey, destinationProvider: extra.destinationProvider,
    source: ctx.lastTouch.utm_source, medium: ctx.lastTouch.utm_medium,
    campaignId: ctx.lastTouch.utm_id || ctx.lastTouch.campaign_id,
    campaignName: ctx.lastTouch.utm_campaign, content: ctx.lastTouch.utm_content, term: ctx.lastTouch.utm_term,
    gclid: ctx.lastTouch.gclid, fbclid: ctx.lastTouch.fbclid,
    referrer: ctx.lastTouch.referrer || req.headers.referer || '', path: url.pathname,
    deviceCategory: classifyDevice(req.headers['user-agent'] || ''),
    language: String(req.headers['accept-language'] || '').split(',')[0].slice(0, 20),
    firstTouch: ctx.firstTouch, lastTouch: ctx.lastTouch,
    metadata: extra.metadata || {}, occurredAt: new Date().toISOString(),
  };
}

function landingHtml() {
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex,nofollow"><title>AKIMITSU · Da Nang</title><style>
  :root{--bg:#f3ede2;--ink:#171512;--muted:#746d63;--line:#d8cdbb;--accent:#8b2525}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh;display:grid;place-items:center;padding:24px}.card{width:min(520px,100%);padding:36px 28px 24px;border:1px solid var(--line);background:rgba(255,255,255,.35);box-shadow:0 18px 55px rgba(52,41,24,.08)}.eyebrow{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);margin-bottom:12px}h1{font-family:Georgia,"Times New Roman",serif;font-size:44px;letter-spacing:.06em;margin:0 0 8px}.sub{color:var(--muted);font-size:14px;margin-bottom:30px}.actions{display:grid;gap:10px}.btn{display:flex;align-items:center;justify-content:space-between;text-decoration:none;color:var(--ink);border:1px solid var(--line);padding:16px 17px;background:#faf6ef;font-weight:650}.btn.primary{background:var(--ink);color:white;border-color:var(--ink)}.btn span:last-child{opacity:.55}.note{margin-top:22px;color:var(--muted);font-size:11px;line-height:1.5;text-align:center}.mark{height:2px;background:var(--accent);width:44px;margin:0 0 24px}@media(max-width:480px){.card{padding:30px 20px 20px}h1{font-size:36px}}
  </style></head><body><main class="card"><div class="eyebrow">Tokyo Asakusa · Da Nang</div><div class="mark"></div><h1>AKIMITSU</h1><div class="sub">Tempura · Sushi · Japanese Dining</div><div class="actions"><a class="btn primary" href="/r/menu"><span>Xem menu</span><span>↗</span></a><a class="btn" href="/r/order"><span>Order tại nhà hàng</span><span>↗</span></a><a class="btn" href="/r/maps"><span>Chỉ đường</span><span>↗</span></a><a class="btn" href="/r/call"><span>Gọi nhà hàng</span><span>↗</span></a></div><div class="note">Official links are provided by the restaurant's current menu and ordering systems.</div></main></body></html>`;
}

async function handle(req, res) {
  const host = String(req.headers.host || 'akimitsu.store').split(':')[0];
  const url = new URL(req.url || '/', `https://${host}`);
  if (url.pathname === '/healthz') return json(res, 200, { ok: true, service: 'hangdoi-measurement', version: '0.1.0', db: dbMode() });

  if (url.pathname.startsWith('/api/performance')) {
    const suppliedToken = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '') || String(req.headers['x-api-key'] || '');
    if (!config.apiToken && config.env === 'production') return json(res, 503, { error: 'api_token_not_configured' });
    if (config.apiToken && suppliedToken !== config.apiToken) return json(res, 401, { error: 'unauthorized' });
    const days = Math.min(Math.max(Number(url.searchParams.get('days') || 30), 1), 365);
    const since = new Date(Date.now() - days * 86400000).toISOString();
    return json(res, 200, { project: akimitsu.id, days, ...(await eventSummary(akimitsu.id, since)) });
  }

  const goHost = host === 'go.akimitsu.store';
  const directKey = goHost ? url.pathname.replace(/^\//, '') : '';
  const routeKey = url.pathname.startsWith('/r/') ? url.pathname.slice(3) : directKey;
  if (routeKey && akimitsu.destinations[routeKey]) {
    const destination = akimitsu.destinations[routeKey];
    const ctx = clientContext(req, url);
    if (!isLikelyBot(req.headers['user-agent'] || '')) {
      await recordEvent(toEvent(req, url, ctx, destination.eventName, { destinationKey: routeKey, destinationProvider: destination.provider }));
    }
    res.writeHead(302, { Location: destination.url, 'Set-Cookie': ctx.setCookies, 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow' });
    return res.end();
  }

  if (url.pathname === '/' || url.pathname === '/menu') {
    const ctx = clientContext(req, url);
    if (!isLikelyBot(req.headers['user-agent'] || '')) await recordEvent(toEvent(req, url, ctx, 'page_view'));
    return send(res, 200, landingHtml(), 'text/html; charset=utf-8', { 'Set-Cookie': ctx.setCookies, 'X-Robots-Tag': 'noindex, nofollow' });
  }

  return json(res, 404, { error: 'not_found' });
}

if (config.autoMigrate) await migrate();
const server = http.createServer((req, res) => handle(req, res).catch(err => { console.error(err); json(res, 500, { error: 'internal_error' }); }));
server.listen(config.port, '0.0.0.0', () => console.log(`hangdoi-measurement listening on :${config.port} (${dbMode()})`));
