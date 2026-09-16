import { migrate, closeDb, dbMode } from '../src/db.js';

try {
  await migrate();
  console.log(`Migration complete (${dbMode()}).`);
} finally {
  await closeDb();
}
