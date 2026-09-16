export const config = {
  env: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT || 3000),
  databaseUrl: process.env.DATABASE_URL || '',
  eventStorePath: process.env.EVENT_STORE_PATH || '',
  autoMigrate: String(process.env.AUTO_MIGRATE || 'false').toLowerCase() === 'true',
  cookieSecure: String(process.env.COOKIE_SECURE || (process.env.NODE_ENV === 'production' ? 'true' : 'false')).toLowerCase() === 'true',
  sessionTtlMinutes: Number(process.env.SESSION_TTL_MINUTES || 30),
  apiToken: process.env.MEASUREMENT_API_TOKEN || '',
};
