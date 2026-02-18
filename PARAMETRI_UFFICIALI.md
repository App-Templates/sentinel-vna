# PARAMETRI UFFICIALI SENTINEL
## Fonte: PRD + CTO Review (cto-data) — USARE SEMPRE QUESTI

### Soglie Severity (A1 - Revenue Anomaly)
| Severity | drop_percent | duration_hours |
|----------|-------------|----------------|
| P0       | -15%        | 2              |
| P1       | -10%        | 2              |
| P2       | -5%         | 4              |

### Baseline
- **Metodo:** Media 7 same-weekday same-hour (7 settimane)
- **Codice:** `range(1, 8)` — **MAI** `range(1, 5)`
- **Soglia minima:** 4 data points per baseline valida

### Z-Score
- **Tipo:** Sample standard deviation (Bessel's correction)
- **Codice:** `ddof=1` oppure divisore `(N-1)` — **MAI** population std `(N)`

### Drift Detection (A2)
- window_days: 7
- threshold_percent: -8%

### Near-Zero (A3)
- revenue_threshold_eur: 100
- coverage_threshold: 0.05
- consecutive_periods: 3

### Data Gap (A0)
- max_gap_hours: 4
- severity: P1

### Triage
- traffic_driven_threshold: -10%
- coverage_driven_threshold: -10%
- **Labels SEMPRE UPPERCASE:** TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, REVENUE_ONLY

### Environment Keys
- **SEMPRE:** WEB, AMP, APP
- **MAI:** desktop, mobile_web, mobile_app

### Scheduler
- A1+A3: ogni 2 ore
- A2 drift: ogni 6 ore
- Recheck: ogni 5 minuti

### Data Sources
- athena_retry_count: 1 (2 tentativi totali)
- athena_timeout_seconds: 30
- cache_ttl_hours: 24
- Fallback: Athena → GAM → Parquet → BLOCKED (no synthetic in LIVE)

### Top Publishers
- top_n contributors: 15
- min_quota_percent: 1%
- Geo clusters: ITA=[IT], ES=[ES], OTHER=[BR,MX,AR,PT,CO,CL,PE,US,UK,FR,DE]
