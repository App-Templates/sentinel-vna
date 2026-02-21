---
phase: 06-revisione-documentale
plan: 02
subsystem: operational-docs
tags: [documentation, operator-workflow, feedback, assignment, intervention]
dependency_graph:
  requires: [06-01, 03-operator-workflow]
  provides: [operator-workflow-docs]
  affects: [DocsPage]
tech_stack:
  added: []
  patterns: [section-expansion, faq-extension]
key_files:
  created: []
  modified:
    - frontend/src/pages/DocsPage.tsx
decisions:
  - key: "Three dedicated sections for operator workflow"
    rationale: "Separating feedback, assignment, and intervention into distinct sections improves discoverability and clarity vs single workflow section"
  - key: "Operator workflow sections placed after FAQ"
    rationale: "FAQ is foundational knowledge; operator workflow is advanced operational features"
  - key: "Inline feedback loop explanation in pipeline section"
    rationale: "Shows how Phase 3 integrates with existing pipeline architecture without creating duplicate pipeline documentation"
metrics:
  duration_hours: 0.03
  tasks_completed: 3
  files_modified: 1
  commits: 3
  completed_at: "2026-02-21"
---

# Phase 06 Plan 02: Operator Workflow Documentation Summary

Operational documentation for Phase 3 operator workflow features — feedback system with 6 categories, alert assignment with @adkaora.com validation, and intervention tracking with baseline exclusion mechanism.

## Objective

Document the operator workflow features built in Phase 3 so TAM&Yield team members understand how to provide feedback, assign alerts, and track manual interventions to build operational knowledge and prevent recurring false positives.

## Tasks Completed

### Task 1: Add operator workflow sections to operational docs
**Commit:** e172c32
**Files:** frontend/src/pages/DocsPage.tsx

Added three new sections to OP_SECTIONS array and OperationalDocs component:

**Section 1 - operator-workflow-feedback (Feedback e Apprendimento):**
- Documents all 6 feedback categories: REAL + 5 FALSE_POSITIVE variants (MANUAL_INTERVENTION, SEASONALITY, TECHNICAL, PUBLISHER_CAMPAIGN, MARKET_NOISE)
- Explains publisher feedback history feature (system shows previous feedback on same publisher)
- Provides clear usage instructions: select category from panel, add comment, save

**Section 2 - operator-workflow-assignment (Assegnazione Alert):**
- Explains assignment system for team workload distribution
- Highlights email validation requirement (@adkaora.com only, enforced at database level)
- Documents how to assign via dropdown and filter dashboard by assigned_to

**Section 3 - operator-workflow-intervention (Tracking Interventi Manuali):**
- Lists 6 intervention types: FLOOR_PRICE_CHANGE, MCM_CONFIG, TARGETING_CHANGE, AD_UNIT_CHANGE, BLOCK_LIST, OTHER
- Explains required fields (publisher, type, timestamp, reason) and optional fields (value before/after)
- Documents baseline exclusion mechanism: entire hour of intervention timestamp excluded from future baseline calculations
- Clarifies two save modes: Quick Log (standalone) vs Link to Alert (connected to current alert)

### Task 2: Update pipeline section for Phase 3 integration
**Commit:** 6c38938
**Files:** frontend/src/pages/DocsPage.tsx

Modified pipeline section to reflect Phase 3 integration:
- Updated Data Fetcher (step 2) description to mention "Esclude periodi con interventi manuali registrati"
- Added blue callout box "Operator Feedback Loop (Phase 3)" explaining how operators provide feedback, assign alerts, and track interventions
- Explains that interventions are excluded from baseline to prevent recurring alerts on known changes

### Task 3: Update FAQ section with operator workflow questions
**Commit:** 8388cc8
**Files:** frontend/src/pages/DocsPage.tsx

Added three new FAQ items before the "Intelligenza Multi-Metrica" separator:

1. **"Come faccio a marcare un alert come falso positivo?"**
   - Answer: Use Feedback panel, select FALSE_POSITIVE category (5 variants), add comment, save. Feedback visible in publisher history.

2. **"Se registro un intervento manuale, il sistema smetterà di alertare su quel calo?"**
   - Answer: Partially yes. The intervention hour is excluded from future baseline calculations. Example: floor price change at 14:00 Tuesday won't affect Tuesday 14:00 baseline going forward.

3. **"Posso vedere lo storico degli interventi su un publisher?"**
   - Answer: Not yet in UI (future phase). API endpoint available: GET /api/publishers/{publisher_id}/interventions.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification checks passed:

1. ✅ Three new operator workflow sections exist (feedback, assignment, intervention)
2. ✅ Feedback categories (REAL + 5 FALSE_POSITIVE variants) documented in operator-workflow-feedback section
3. ✅ Email validation (@adkaora.com) mentioned in assignment section
4. ✅ Baseline exclusion logic explained in intervention section (entire hour excluded)
5. ✅ Pipeline section mentions operator feedback loop integration with blue callout box
6. ✅ FAQ section includes three operator workflow questions with clear answers

## Success Criteria Met

- ✅ Operator reading docs understands all 6 feedback categories and when to use each
- ✅ Assignment email validation requirement (@adkaora.com) is clear
- ✅ Intervention tracking workflow documented (quick log vs link to alert modes)
- ✅ Baseline exclusion mechanism explained (excludes hour of intervention from 7-week same-hour calculation)
- ✅ Operators know where to find historical feedback (publisher alert detail) and interventions (API endpoint)

## Key Technical Details

**Documentation Structure:**
- OP_SECTIONS array extended from 16 to 19 sections (added 3 operator workflow sections)
- Sections placed after FAQ to maintain logical flow (foundational → advanced)
- Used consistent Section component pattern with icon, title, collapsible content

**Coverage:**
- Feedback taxonomy: All 6 categories documented with clear use cases
- Assignment system: Email validation, one-per-alert constraint, filtering explained
- Intervention tracking: 6 intervention types, baseline exclusion mechanism, two save modes
- Integration: Pipeline section updated to show how Phase 3 fits into existing architecture

**User Guidance:**
- FAQ answers provide step-by-step workflows
- Baseline exclusion explained with concrete example (Tuesday 14:00 floor price change)
- Blue callout boxes highlight important operational concepts
- API endpoint documented for power users needing intervention history

## Self-Check: PASSED

All files created and commits exist:

✅ **Files modified:**
- frontend/src/pages/DocsPage.tsx (95 insertions in task 1, 8 in task 2, 3 in task 3)

✅ **Commits:**
- e172c32: Task 1 - operator workflow sections
- 6c38938: Task 2 - pipeline section update
- 8388cc8: Task 3 - FAQ section update

✅ **Content verification:**
```bash
# Verified operator workflow sections exist
grep "operator-workflow-feedback" frontend/src/pages/DocsPage.tsx
grep "operator-workflow-assignment" frontend/src/pages/DocsPage.tsx
grep "operator-workflow-intervention" frontend/src/pages/DocsPage.tsx

# Verified feedback categories documented
grep "REAL.*FALSE_POSITIVE" frontend/src/pages/DocsPage.tsx

# Verified pipeline integration
grep "Esclude periodi" frontend/src/pages/DocsPage.tsx
grep "Operator Feedback Loop" frontend/src/pages/DocsPage.tsx

# Verified FAQ additions
grep "falso positivo" frontend/src/pages/DocsPage.tsx
grep "intervento manuale" frontend/src/pages/DocsPage.tsx
grep "storico degli interventi" frontend/src/pages/DocsPage.tsx
```

## Impact

**For Operators:**
- Clear understanding of how to provide meaningful feedback (6 categories vs generic good/bad)
- Awareness of baseline exclusion benefit (record intervention once, prevent future false positives)
- Knowledge of assignment system for team coordination
- Reference documentation for all Phase 3 workflow features

**For Product:**
- Operational features now discoverable (previously undocumented)
- Reduces training burden (docs serve as self-service guide)
- Establishes pattern for future workflow feature documentation

**For System:**
- DocsPage now reflects Phase 1-4 capabilities (Phase 1 comparative alerting already documented in 06-01, Phase 3 operator workflow documented here, Phase 4 Slack notifications to be documented in 06-03)
- Closes documentation gap identified in Phase 6 audit
