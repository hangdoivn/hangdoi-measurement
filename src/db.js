import { Pool } from 'pg';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from './config.js';

const pool = config.databaseUrl ? new Pool({
  connectionString: config.databaseUrl,
  ssl: config.env === 'production' ? { rejectUnauthorized: false } : false,
}) : null;

const memoryEvents = [];

export function dbMode() {
  return pool ? 'postgres' : 'memory';
}

export async function migrate() {
  if (!pool) return;
  const here = path.dirname(fileURLToPath(import.meta.url));
  const sql = await fs.readFile(path.resolve(here, '../db/migrations/001_init.sql'), 'utf8');
  await pool.query(sql);
}

export async function recordEvent(event) {
  if (!pool) {
    memoryEvents.push(event);
    if (memoryEvents.length > 50000) memoryEvents.shift();
    return;
  }

  await pool.query(`
    INSERT INTO events (
      event_id, workspace_id, project_id, visitor_id, session_id, event_name,
      destination_key, destination_provider, source, medium, campaign_id, campaign_name,
      content, term, gclid, fbclid, referrer, path, device_category, language, metadata, occurred_at
    ) VALUES (
      $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21::jsonb,$22
    ) ON CONFLICT (event_id) DO NOTHING
  `, [
    event.eventId, event.workspaceId, event.projectId, event.visitorId, event.sessionId, event.eventName,
    event.destinationKey || null, event.destinationProvider || null, event.source || null, event.medium || null,
    event.campaignId || null, event.campaignName || null, event.content || null, event.term || null,
    event.gclid || null, event.fbclid || null, event.referrer || null, event.path || null,
    event.deviceCategory || null, event.language || null, JSON.stringify(event.metadata || {}), event.occurredAt,
  ]);
}

export async function eventSummary(projectId, sinceIso) {
  if (!pool) {
    const rows = memoryEvents.filter(event => event.projectId === projectId && event.occurredAt >= sinceIso);
    const counts = {};
    for (const row of rows) counts[row.eventName] = (counts[row.eventName] || 0) + 1;
    return { counts, total: rows.length, mode: 'memory' };
  }

  const result = await pool.query(`
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
