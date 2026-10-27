# backend/db/models.py CHECK Cross-Check

**Generated:** 2026-04-22T20:57:00Z

## ORM Declaration (backend/db/models.py)

```python
# models.py:32-35 — ChannelGroup enum
class ChannelGroup(str, Enum):
    GOOGLE = "GOOGLE"
    OPEN_BIDDING = "OPEN_BIDDING"

# models.py:173-176 — SQL_CREATE_ALERTS (channel_group and alert_rule CHECK)
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    ...
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7')),
```

Relevant code block from `SQL_CREATE_ALERTS` (models.py lines 169-191):
```sql
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7')),
    ...
);
```

## Comparison Matrix

| Source | channel_group CHECK values | alert_rule CHECK values | File/Line |
|--------|----------------------------|------------------------|-----------|
| backend/db/models.py (SQL_CREATE_ALERTS) | `'GOOGLE', 'OPEN_BIDDING'` | `'A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7'` | models.py:174, 176 |
| HEAD DB (head-schema.sql) | `'GOOGLE', 'OPEN_BIDDING'` | `'A0', 'A1', 'A2', 'A3'` | head-schema.sql |
| WIP DB (wip-schema.sql) | `'GOOGLE', 'OPEN_BIDDING'` | `'A0', 'A1', 'A2', 'A3'` | wip-schema.sql |
| v1.2 runtime write payload (intel) | GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING | A0-A7 (all alert types) | intel/deep-audit-evening.md |

## Findings

- [x] Python ORM (`ChannelGroup` enum + SQL_CREATE_ALERTS channel_group CHECK) matches HEAD DB: **YES** — both have `('GOOGLE', 'OPEN_BIDDING')`
- [x] Python ORM (`ChannelGroup` enum + SQL_CREATE_ALERTS channel_group CHECK) matches WIP DB: **YES** — WIP also has `('GOOGLE', 'OPEN_BIDDING')`
- [ ] Python ORM matches v1.2 runtime payload: **NO** — v1.2 pipeline writes 7 channels (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING) but ORM still declares only 2 channels. This is the core silent-failure mismatch.
- [ ] Python ORM `alert_rule` matches DB (HEAD or WIP): **NO** — models.py SQL_CREATE_ALERTS declares `('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7')` but both DBs only have `('A0', 'A1', 'A2', 'A3')`. A5/A6/A7 were added to the Python enum (models.py:27-29) and SQL string but never applied to the running DB schema via a migration.
- [x] Silent-failure root cause confirmed: **YES** — The `channel_group` CHECK `IN ('GOOGLE', 'OPEN_BIDDING')` in the DB rejects all 7 v1.2 channel values (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING) at INSERT time, causing 2590 pipeline runs to produce zero alerts since 2026-01-22.

**Additional finding**: The `alert_rule` CHECK discrepancy (DB: A0-A3 only; ORM/code: A0-A7) means that any attempt to INSERT an A5/A6/A7 alert would ALSO fail silently. This is a second silent-failure vector beyond the channel_group issue.

## Implication for Phase 08

Phase 08 (SCHEMA-01/02) must perform two schema updates to the `alerts` table: (1) expand `channel_group` CHECK to include all 7 v1.2 channels, AND (2) expand `alert_rule` CHECK to include A5, A6, A7 — matching the existing models.py `SQL_CREATE_ALERTS` declaration. Phase 08 should also sync `ChannelGroup` enum in models.py to include the 7 new channels (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING). The 5 tables added in WIP (alert_feedback, alert_assignments, manual_interventions, alert_intervention_links, pending_notifications) are already correct in both WIP DB and models.py and do not require schema changes — they only need to be forward-ported from WIP to HEAD via a baseline migration.
