import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from './config.js';

let pool = null;
const memoryEvents = [];

async function getPool() {
  if (!config.databaseUrl) return null;
  if (pool) return pool;
  const { Pool } = await import('pg');
  pool = new Pool({
    connectionString: config.databaseUrl,
    ssl: config.env === 'production' ? { rejectUnauthorized: false } : false,
  });
  return pool;
}

export function dbMode() {
  if (config.databaseUrl) return 'postgres';
  if (config.eventStorePath) return 'file';
  return 'memory';
}

async function ensureEventStoreDir() {
  if (!config.eventStorePath) return;
  await fs.mkdir(path.dirname(config.eventStorePath), { recursive: true });
}

export async function migrate() {
  const activePool = await getPool();
  if (!activePool) {
    await ensureEventStoreDir();
    return;
  }
  const here = path.dirname(fileURLToPath(import.meta.url));
  const sql = await fs.readFile(path.resolve(here, '../db/migrations/001_init.sql'), 'utf8');
  await activePool.query(sql);
}

export async function recordEvent(event) {
  if (config.eventStorePath && !config.databaseUrl) {
    await ensureEventStoreDir();
    await fs.appendFile(config.eventStorePath, `${JSON.stringify(event)}\n`, 'utf8');
    return;
  }

  const activePool = await getPool();
  if (!activePool) {
    memoryEvents.push(event);
    if (memoryEvents.length > 50000) memoryEvents.shift();
    return;
  }

  await activePool.query(`
    INSERT INTO events (
      event_id, workspace_id, project_id, visitor_id, session_id, event_name,
      destination_key, destination_provider, source, medium, campaign_id, campaign_name,
      content, term, gclid, fbclid, referrer, path, device_category, language,
      first_touch, last_touch, metadata, occurred_at
    ) VALUES (
      $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
      $21::jsonb,$22::jsonb,$23::jsonb,$24
    ) ON CONFLICT (event_id) DO NOTHING
  `, [
    event.eventId, event.workspaceId, event.projectId, event.visitorId, event.sessionId, event.eventName,
    event.destinationKey || null, event.destinationProvider || null, event.source || null, event.medium || null,
    event.campaignId || null, event.campaignName || null, event.content || null, event.term || null,
    event.gclid || null, event.fbclid || null, event.referrer || null, event.path || null,
    event.deviceCategory || null, event.language || null,
    JSON.stringify(event.firstTouch || {}), JSON.stringify(event.lastTouch || {}), JSON.stringify(event.metadata || {}),
    event.occurredAt,
  ]);
}

async function fileEvents(projectId, sinceIso) {
  try {
    const content = await fs.readFile(config.eventStorePath, 'utf8');
    return content.split('\n').filter(Boolean).flatMap(line => {
      try {
        const event = JSON.parse(line);
        return event.projectId === projectId && event.occurredAt >= sinceIso ? [event] : [];
      } catch {
        return [];
      }
    });
  } catch (error) {
    if (error?.code === 'ENOENT') return [];
    throw error;
  }
}

export async function eventSummary(projectId, sinceIso) {
  if (config.eventStorePath && !config.databaseUrl) {
    const rows = await fileEvents(projectId, sinceIso);
    const counts = {};
    for (const row of rows) counts[row.eventName] = (counts[row.eventName] || 0) + 1;
    return { counts, total: rows.length, mode: 'file' };
  }

  const activePool = await getPool();
  if (!activePool) {
    const rows = memoryEvents.filter(event => event.projectId === projectId && event.occurredAt >= sinceIso);
    const counts = {};
    for (const row of rows) counts[row.eventName] = (counts[row.eventName] || 0) + 1;
    return { counts, total: rows.length, mode: 'memory' };
  }

  const result = await activePool.query(`
    SELECT event_name, COUNT(*)::int AS count
    FROM events
    WHERE project_id = $1 AND occurred_at >= $2::timestamptz
    GROUP BY event_name
    ORDER BY count DESC
  `, [projectId, sinceIso]);

  const counts = Object.fromEntries(result.rows.map(row => [row.event_name, row.count]));
  return {
    counts,
    total: result.rows.reduce((sum, row) => sum + row.count, 0),
    mode: 'postgres',
  };
}

export async function closeDb() {
  if (pool) await pool.end();
}
