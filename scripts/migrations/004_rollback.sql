-- Rollback for migration 004_canonicalize_alerts_created_at
--
-- ONE-WAY NOTE: Format normalization is destructive -- pre-migration format
-- variance (aware vs naive, T vs space) is lost after apply. This rollback
-- ONLY removes the ledger row (so `_already_applied` returns False).
--
-- To fully revert row contents, restore from pre-phase-10.1 backup:
--   cp data/vna_alerts.db.pre-phase10.1.bak data/vna_alerts.db

BEGIN TRANSACTION;

DELETE FROM vna_schema_migrations
 WHERE migration_id = '004_canonicalize_alerts_created_at';

COMMIT;
