CREATE TABLE IF NOT EXISTS events (
  event_id text PRIMARY KEY,
  workspace_id text NOT NULL,
  project_id text NOT NULL,
  visitor_id text NOT NULL,
  session_id text NOT NULL,
  event_name text NOT NULL,
  destination_key text,
  destination_provider text,
  source text,
  medium text,
  campaign_id text,
  campaign_name text,
  content text,
  term text,
  gclid text,
  fbclid text,
  referrer text,
  path text,
  device_category text,
  language text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_project_time ON events(project_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_campaign ON events(project_id, campaign_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS platform_daily_metrics (
  project_id text NOT NULL,
  platform text NOT NULL,
  metric_date date NOT NULL,
  campaign_id text NOT NULL DEFAULT '',
  metric_key text NOT NULL,
  metric_value numeric NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(project_id, platform, metric_date, campaign_id, metric_key)
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id bigserial PRIMARY KEY,
  project_id text NOT NULL,
  platform text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL,
  detail jsonb NOT NULL DEFAULT '{}'::jsonb
);
