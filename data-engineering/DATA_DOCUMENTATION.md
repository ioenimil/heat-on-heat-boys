# ServiceHub Data Engineering Documentation

**Version:** 1.0  
**Last Updated:** 2026-03-05  
**Owner:** Data Engineering Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Source Schema](#source-schema)
4. [Analytics Schema](#analytics-schema)
5. [ETL Pipeline](#etl-pipeline)
6. [Data Quality Rules](#data-quality-rules)
7. [Metrics Definitions](#metrics-definitions)
8. [Airflow DAGs](#airflow-dags)
9. [Troubleshooting](#troubleshooting)

---

## 1. Overview

The ServiceHub data engineering layer is responsible for:

- **Extracting** operational data from PostgreSQL source tables
- **Transforming** raw data into analytics-ready metrics
- **Loading** aggregated data into analytics tables for dashboard consumption
- **Validating** data quality and quarantining invalid records
- **Seeding** sample data for development and demo environments

### Technology Stack

- **Orchestration:** Apache Airflow 2.8.1
- **Data Processing:** Python 3.11 + Pandas 2.1.3
- **Database:** PostgreSQL 16
- **Scheduler:** LocalExecutor (daily at midnight UTC)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Airflow Scheduler                          │
│                   (LocalExecutor, Daily 00:00 UTC)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    servicehub_etl DAG                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Test DB Conn │→ │ Validate SLA │→ │ Extract &    │         │
│  └──────────────┘  └──────────────┘  │ Validate     │         │
│                                       └──────┬───────┘         │
│                                              ▼                  │
│                                       ┌──────────────┐         │
│                                       │ Transform &  │         │
│                                       │ Load         │         │
│                                       └──────┬───────┘         │
│                                              ▼                  │
│                                       ┌──────────────┐         │
│                                       │ Summary      │         │
│                                       └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                          │
│  ┌────────────────────┐         ┌────────────────────┐         │
│  │  Source Tables     │         │  Analytics Tables  │         │
│  │  ─────────────     │         │  ────────────────  │         │
│  │  service_requests  │    →    │  analytics_sla_metrics       │
│  │  users             │         │  analytics_daily_volume      │
│  │  departments       │         │  analytics_agent_performance │
│  │  sla_policies      │         │  analytics_department_workload│
│  └────────────────────┘         └────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
data-engineering/
├── dags/                      # Airflow DAG definitions
│   ├── servicehub_etl_dag.py  # Main ETL pipeline
│   └── servicehub_seed_dag.py # Sample data seeder
├── extractors/                # Data extraction modules
│   └── db_extractor.py        # PostgreSQL extractors
├── transformers/              # Business logic transformations
│   ├── sla_metrics.py         # SLA compliance calculations
│   ├── daily_volume.py        # Daily ticket volume aggregation
│   ├── agent_performance.py   # Agent performance metrics
│   └── department_workload.py # Department workload metrics
├── loaders/                   # Data loading modules
│   └── db_loader.py           # PostgreSQL loader (REPLACE strategy)
├── validators/                # Data quality validation
│   └── data_quality.py        # Schema and business rule validators
├── seeders/                   # Sample data generation
│   └── sample_data.py         # Faker-based data generator
├── utils/                     # Shared utilities
│   ├── db.py                  # Database connection management
│   └── logger.py              # Structured logging
└── config.py                  # Configuration management
```

---

## 3. Source Schema

### 3.1 service_requests

**Purpose:** Core operational table containing all service tickets

| Column              | Type         | Description                                      |
| ------------------- | ------------ | ------------------------------------------------ |
| id                  | UUID         | Primary key                                      |
| title               | VARCHAR(255) | Request title                                    |
| description         | TEXT         | Detailed description                             |
| category            | VARCHAR(20)  | IT_SUPPORT \| FACILITIES \| HR_REQUEST           |
| priority            | VARCHAR(10)  | CRITICAL \| HIGH \| MEDIUM \| LOW                |
| status              | VARCHAR(15)  | OPEN \| ASSIGNED \| IN_PROGRESS \| RESOLVED \| CLOSED |
| requester_id        | UUID         | FK to users.id                                   |
| assigned_to_id      | UUID         | FK to users.id (nullable)                        |
| department_id       | UUID         | FK to departments.id (nullable)                  |
| created_at          | TIMESTAMPTZ  | Ticket creation timestamp (UTC)                  |
| updated_at          | TIMESTAMPTZ  | Last update timestamp (UTC)                      |
| resolved_at         | TIMESTAMPTZ  | Resolution timestamp (nullable)                  |
| closed_at           | TIMESTAMPTZ  | Closure timestamp (nullable)                     |
| first_response_at   | TIMESTAMPTZ  | First agent response timestamp (nullable)        |
| sla_deadline        | TIMESTAMPTZ  | Calculated SLA deadline (nullable)               |
| is_sla_breached     | BOOLEAN      | TRUE if resolved after sla_deadline              |

**ETL Usage:** Primary source for all analytics transformations

---

### 3.2 sla_policies

**Purpose:** SLA configuration for category-priority combinations

| Column                  | Type        | Description                          |
| ----------------------- | ----------- | ------------------------------------ |
| id                      | UUID        | Primary key                          |
| category                | VARCHAR(20) | IT_SUPPORT \| FACILITIES \| HR_REQUEST |
| priority                | VARCHAR(10) | CRITICAL \| HIGH \| MEDIUM \| LOW    |
| response_time_hours     | INTEGER     | Hours allowed for first response     |
| resolution_time_hours   | INTEGER     | Hours allowed for resolution         |
| created_at              | TIMESTAMPTZ | Policy creation timestamp            |

**ETL Usage:** 
- Validation: Must contain exactly 12 rows (3 categories × 4 priorities)
- Join key for SLA compliance calculations

**Required Rows:**

```sql
IT_SUPPORT + CRITICAL → 1h response, 4h resolution
IT_SUPPORT + HIGH     → 2h response, 8h resolution
IT_SUPPORT + MEDIUM   → 4h response, 24h resolution
IT_SUPPORT + LOW      → 8h response, 48h resolution
FACILITIES + CRITICAL → 1h response, 8h resolution
FACILITIES + HIGH     → 2h response, 16h resolution
FACILITIES + MEDIUM   → 4h response, 48h resolution
FACILITIES + LOW      → 8h response, 96h resolution
HR_REQUEST + CRITICAL → 2h response, 8h resolution
HR_REQUEST + HIGH     → 4h response, 24h resolution
HR_REQUEST + MEDIUM   → 8h response, 72h resolution
HR_REQUEST + LOW      → 24h response, 168h resolution
```

---

### 3.3 users

**Purpose:** User accounts (employees and agents)

| Column      | Type         | Description                          |
| ----------- | ------------ | ------------------------------------ |
| id          | UUID         | Primary key                          |
| email       | VARCHAR(255) | Unique email                         |
| name        | VARCHAR(255) | Full name                            |
| role        | VARCHAR(20)  | USER \| AGENT \| MANAGER             |
| department_id | UUID       | FK to departments.id (nullable)      |
| is_active   | BOOLEAN      | Account status                       |
| created_at  | TIMESTAMPTZ  | Account creation timestamp           |

**ETL Usage:** Denormalization source for agent_name in analytics_agent_performance

---

### 3.4 departments

**Purpose:** Organizational departments

| Column      | Type         | Description                |
| ----------- | ------------ | -------------------------- |
| id          | UUID         | Primary key                |
| name        | VARCHAR(100) | Department name            |
| description | TEXT         | Department description     |
| created_at  | TIMESTAMPTZ  | Creation timestamp         |

**ETL Usage:** Denormalization source for department_name in analytics_department_workload

---

## 4. Analytics Schema

All analytics tables use **REPLACE strategy** (truncate and reload on each ETL run).

### 4.1 analytics_sla_metrics

**Granularity:** One row per (category, priority) combination

**Purpose:** SLA compliance tracking by category and priority

| Column               | Type         | Description                                     |
| -------------------- | ------------ | ----------------------------------------------- |
| category             | VARCHAR(20)  | IT_SUPPORT \| FACILITIES \| HR_REQUEST          |
| priority             | VARCHAR(10)  | CRITICAL \| HIGH \| MEDIUM \| LOW               |
| total_tickets        | INTEGER      | Total tickets for this combination              |
| resolved_tickets     | INTEGER      | Tickets with status RESOLVED or CLOSED          |
| breached_tickets     | INTEGER      | Tickets where is_sla_breached = TRUE            |
| compliance_rate_pct  | NUMERIC(5,2) | (resolved_within_sla / resolved_tickets) × 100  |
| avg_resolution_hours | NUMERIC(8,2) | Mean hours from created_at to resolved_at       |
| avg_response_hours   | NUMERIC(8,2) | Mean hours from created_at to first_response_at |
| last_updated_at      | TIMESTAMPTZ  | ETL run timestamp                               |

**Business Rules:**
- Always contains 12 rows (one per category-priority combination)
- Zero counts for combinations with no tickets
- compliance_rate_pct = 0 when resolved_tickets = 0
- avg_resolution_hours = 0 when no resolved tickets
- avg_response_hours = 0 when no first_response_at values

**Transformer:** `transformers/sla_metrics.py`

---

### 4.2 analytics_daily_volume

**Granularity:** One row per (report_date, category, priority, status) combination

**Purpose:** Daily ticket volume trends

| Column       | Type        | Description                          |
| ------------ | ----------- | ------------------------------------ |
| report_date  | DATE        | Calendar day (UTC)                   |
| category     | VARCHAR(20) | Request category                     |
| priority     | VARCHAR(10) | Request priority                     |
| status       | VARCHAR(15) | Ticket status                        |
| ticket_count | INTEGER     | Tickets created on this date         |
| last_updated_at | TIMESTAMPTZ | ETL run timestamp                 |

**Business Rules:**
- report_date extracted from created_at (date component only)
- Groups by all dimensions: date, category, priority, status
- Includes all status values (OPEN, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED)

**Transformer:** `transformers/daily_volume.py`

---

### 4.3 analytics_agent_performance

**Granularity:** One row per (agent_id, week_start) combination

**Purpose:** Weekly agent performance metrics

| Column                  | Type         | Description                          |
| ----------------------- | ------------ | ------------------------------------ |
| agent_id                | UUID         | FK to users.id                       |
| agent_name              | VARCHAR(255) | Denormalized from users.name         |
| week_start              | DATE         | Monday of ISO week                   |
| tickets_assigned        | INTEGER      | Tickets assigned to agent            |
| tickets_resolved        | INTEGER      | Tickets resolved by agent            |
| avg_resolution_hours    | NUMERIC(8,2) | Mean resolution time                 |
| sla_compliance_rate_pct | NUMERIC(5,2) | % resolved within SLA                |
| last_updated_at         | TIMESTAMPTZ  | ETL run timestamp                    |

**Business Rules:**
- week_start = Monday of ISO week (calculated from created_at)
- Only includes users with role = 'AGENT'
- tickets_assigned counts where assigned_to_id = agent_id
- tickets_resolved counts where assigned_to_id = agent_id AND status IN ('RESOLVED', 'CLOSED')
- sla_compliance_rate_pct = 0 when tickets_resolved = 0

**Transformer:** `transformers/agent_performance.py`

---

### 4.4 analytics_department_workload

**Granularity:** One row per (department_id, week_start) combination

**Purpose:** Weekly department workload tracking

| Column               | Type         | Description                          |
| -------------------- | ------------ | ------------------------------------ |
| department_id        | UUID         | FK to departments.id                 |
| department_name      | VARCHAR(100) | Denormalized from departments.name   |
| week_start           | DATE         | Monday of ISO week                   |
| open_tickets         | INTEGER      | Tickets with status OPEN or ASSIGNED |
| resolved_tickets     | INTEGER      | Tickets resolved                     |
| breached_tickets     | INTEGER      | Tickets with SLA breach              |
| avg_resolution_hours | NUMERIC(8,2) | Mean resolution time                 |
| last_updated_at      | TIMESTAMPTZ  | ETL run timestamp                    |

**Business Rules:**
- week_start = Monday of ISO week (calculated from created_at)
- open_tickets counts status IN ('OPEN', 'ASSIGNED')
- resolved_tickets counts status IN ('RESOLVED', 'CLOSED')
- breached_tickets counts is_sla_breached = TRUE

**Transformer:** `transformers/department_workload.py`

---

## 5. ETL Pipeline

### 5.1 Pipeline Flow

**DAG ID:** `servicehub_etl`  
**Schedule:** Daily at 00:00 UTC  
**Execution Strategy:** Sequential (max_active_runs=1)

#### Task Sequence

```
1. test_connection
   ↓
2. validate_sla_policies
   ↓
3. extract_and_validate
   ↓
4. transform_and_load
   ↓
5. pipeline_summary
```

---

### 5.2 Task Descriptions

#### Task 1: test_connection

**Purpose:** Verify database connectivity before pipeline execution

**Actions:**
- Establish SQLAlchemy engine connection
- Execute test query: `SELECT 1`
- Fail fast if connection unavailable

**Failure Scenarios:**
- Invalid DB credentials
- PostgreSQL service down
- Network connectivity issues

---

#### Task 2: validate_sla_policies

**Purpose:** Ensure SLA policies table is properly seeded

**Validation Rules:**
- Table must not be empty
- Must contain exactly 12 rows
- Must have all 3 categories × 4 priorities combinations
- No NULL values in category, priority, response_time_hours, resolution_time_hours

**Failure Scenarios:**
- Empty sla_policies table (backend seed not run)
- Missing category-priority combinations
- Invalid data types or NULL values

---

#### Task 3: extract_and_validate

**Purpose:** Extract source data and validate data quality

**Actions:**
1. Extract service_requests table
2. Extract sla_policies table
3. Validate service_requests schema
4. Apply business rule validations
5. Separate clean records from quarantined records
6. Push XCom metrics: raw_row_count, clean_row_count, quarantine_row_count

**Validation Rules:**
- Required columns present: id, category, priority, status, created_at
- Valid enum values for category, priority, status
- created_at is not NULL and is valid timestamp
- resolved_at <= NOW() (no future timestamps)
- resolved_at >= created_at (logical timestamp order)

**Quarantine Reasons:**
- Missing required columns
- Invalid enum values
- NULL created_at
- Future timestamps
- Illogical timestamp sequences

---

#### Task 4: transform_and_load

**Purpose:** Transform clean data and load into analytics tables

**Actions:**
1. Re-extract and validate source data
2. Execute 4 parallel transformations:
   - analytics_sla_metrics
   - analytics_daily_volume
   - analytics_agent_performance
   - analytics_department_workload
3. Load each transformed DataFrame to PostgreSQL
4. Push XCom load_results: {table_name: row_count}

**Load Strategy:** REPLACE (truncate and reload)

**Failure Handling:**
- Transformer failures logged but do not stop pipeline
- Loader failures logged but do not stop pipeline
- Pipeline fails only if ALL transformers or ALL loaders fail

---

#### Task 5: pipeline_summary

**Purpose:** Log pipeline execution summary

**Actions:**
- Pull XCom metrics from previous tasks
- Log summary: raw_row_count, clean_row_count, quarantine_row_count, load_results
- Always executes (trigger_rule=ALL_DONE)

---

### 5.3 Retry Configuration

**Default Retry Policy:**
- Retries: 2
- Retry Delay: 5 minutes
- Exponential Backoff: Enabled
- Depends on Past: False

**Retry Behavior:**
- Transient database errors (connection timeout, deadlock)
- Temporary network issues
- Resource contention

**No Retry:**
- Data quality validation failures
- Schema mismatches
- Business rule violations

---

## 6. Data Quality Rules

### 6.1 Schema Validation

**Required Columns:**
```python
REQUIRED_COLUMNS = [
    'id', 'category', 'priority', 'status', 'created_at',
    'requester_id', 'assigned_to_id', 'department_id',
    'resolved_at', 'first_response_at', 'sla_deadline', 'is_sla_breached'
]
```

**Validation:** All columns must exist in extracted DataFrame

---

### 6.2 Enum Validation

**Valid Categories:**
```python
VALID_CATEGORIES = {'IT_SUPPORT', 'FACILITIES', 'HR_REQUEST'}
```

**Valid Priorities:**
```python
VALID_PRIORITIES = {'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'}
```

**Valid Statuses:**
```python
VALID_STATUSES = {'OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'}
```

**Validation:** All values must match enum sets (case-sensitive)

---

### 6.3 Timestamp Validation

**Rules:**
1. `created_at` must not be NULL
2. `created_at` must be valid UTC timestamp
3. `resolved_at` must be <= NOW() (no future timestamps)
4. `resolved_at` must be >= `created_at` (logical order)
5. `first_response_at` must be >= `created_at` (if not NULL)

**Validation:** Timestamps converted to pandas datetime with UTC timezone

---

### 6.4 SLA Policy Validation

**Rules:**
1. Table must contain exactly 12 rows
2. All category-priority combinations must exist
3. No NULL values in response_time_hours or resolution_time_hours
4. response_time_hours > 0
5. resolution_time_hours > 0

**Validation:** Executed in validate_sla_policies task

---

### 6.5 Quarantine Logging

**Quarantine Summary Format:**
```
========== Quarantine Summary ==========
Total quarantined: 15
Reasons:
  - invalid_category: 5
  - future_timestamp: 3
  - missing_created_at: 7
========================================
```

**Quarantine Columns:**
- All original columns
- `quarantine_reason`: String describing validation failure

---

## 7. Metrics Definitions

### 7.1 SLA Compliance Rate

**Formula:**
```
compliance_rate_pct = (resolved_within_sla / resolved_tickets) × 100
```

**Where:**
- `resolved_within_sla` = COUNT(tickets WHERE resolved_at <= sla_deadline AND status IN ('RESOLVED', 'CLOSED'))
- `resolved_tickets` = COUNT(tickets WHERE status IN ('RESOLVED', 'CLOSED'))

**Edge Cases:**
- Returns 0.0 when resolved_tickets = 0
- Rounds to 2 decimal places

---

### 7.2 Average Resolution Hours

**Formula:**
```
avg_resolution_hours = MEAN((resolved_at - created_at) / 3600)
```

**Where:**
- Only includes tickets with status IN ('RESOLVED', 'CLOSED')
- Only includes tickets with non-NULL resolved_at
- Converts seconds to hours (divide by 3600)

**Edge Cases:**
- Returns 0.0 when no resolved tickets
- Rounds to 2 decimal places

---

### 7.3 Average Response Hours

**Formula:**
```
avg_response_hours = MEAN((first_response_at - created_at) / 3600)
```

**Where:**
- Only includes tickets with non-NULL first_response_at
- Converts seconds to hours (divide by 3600)

**Edge Cases:**
- Returns 0.0 when no first_response_at values
- Rounds to 2 decimal places

---

### 7.4 SLA Breach Detection

**Formula:**
```
is_sla_breached = (resolved_at > sla_deadline) AND status IN ('RESOLVED', 'CLOSED')
```

**Where:**
- `sla_deadline` = created_at + resolution_time_hours (from sla_policies)
- Only applies to resolved/closed tickets

**Edge Cases:**
- FALSE when sla_deadline is NULL
- FALSE when ticket is not resolved

---

### 7.5 Week Start Calculation

**Formula:**
```python
week_start = created_at - timedelta(days=created_at.weekday())
```

**Where:**
- Uses ISO 8601 week definition (Monday = week start)
- Returns date component only (no time)

**Example:**
- created_at = 2026-03-05 (Thursday) → week_start = 2026-03-02 (Monday)

---

## 8. Airflow DAGs

### 8.1 servicehub_etl

**Purpose:** Main ETL pipeline for analytics table refresh

**Configuration:**
```python
dag_id = "servicehub_etl"
schedule = "0 0 * * *"  # Daily at midnight UTC
start_date = datetime(2025, 1, 1)
catchup = False
max_active_runs = 1
tags = ["servicehub", "etl"]
```

**Tasks:** 5 (see section 5.2)

**SLA:** None (best-effort daily refresh)

---

### 8.2 servicehub_seed

**Purpose:** Generate sample data for development/demo environments

**Configuration:**
```python
dag_id = "servicehub_seed"
schedule = None  # Manual trigger only
start_date = datetime(2025, 1, 1)
catchup = False
tags = ["servicehub", "seed"]
```

**Tasks:**
1. seed_users (5 agents, 20 employees)
2. seed_departments (3 departments)
3. seed_tickets (200 tickets over 60 days)

**Data Distribution:**
- IT_SUPPORT: 50%, FACILITIES: 25%, HR_REQUEST: 25%
- CRITICAL: 10%, HIGH: 25%, MEDIUM: 45%, LOW: 20%
- OPEN: 15%, ASSIGNED: 10%, IN_PROGRESS: 20%, RESOLVED: 40%, CLOSED: 15%
- SLA breach rate: ~15%

---

## 9. Troubleshooting

### 9.1 Common Errors

#### Error: "sla_policies table is empty"

**Cause:** Backend seed script has not run or failed

**Solution:**
```sql
-- Run postgres-init/02_seed_sla_policies.sql
-- Or manually insert 12 rows into sla_policies table
```

---

#### Error: "clean_df is empty after validation"

**Cause:** All source records failed data quality validation

**Solution:**
1. Check quarantine summary in Airflow logs
2. Identify most common quarantine_reason
3. Fix source data or adjust validation rules

---

#### Error: "all loader operations failed"

**Cause:** Database permissions or table schema mismatch

**Solution:**
1. Verify analytics_* tables exist
2. Check PostgreSQL user permissions (INSERT, TRUNCATE)
3. Verify column names match OUTPUT_COLUMNS in transformers

---

#### Error: "SQLAlchemy connection timeout"

**Cause:** Database connection pool exhausted or network issue

**Solution:**
1. Check PostgreSQL max_connections setting
2. Verify DB_HOST, DB_PORT in airflow.env
3. Check network connectivity between Airflow and PostgreSQL

---

### 9.2 Monitoring Queries

#### Check Last ETL Run

```sql
SELECT 
    MAX(last_updated_at) as last_etl_run,
    NOW() - MAX(last_updated_at) as time_since_last_run
FROM analytics_sla_metrics;
```

---

#### Check Analytics Table Row Counts

```sql
SELECT 
    'analytics_sla_metrics' as table_name, 
    COUNT(*) as row_count 
FROM analytics_sla_metrics
UNION ALL
SELECT 
    'analytics_daily_volume', 
    COUNT(*) 
FROM analytics_daily_volume
UNION ALL
SELECT 
    'analytics_agent_performance', 
    COUNT(*) 
FROM analytics_agent_performance
UNION ALL
SELECT 
    'analytics_department_workload', 
    COUNT(*) 
FROM analytics_department_workload;
```

---

#### Check SLA Compliance by Category

```sql
SELECT 
    category,
    ROUND(AVG(compliance_rate_pct), 2) as avg_compliance_pct,
    SUM(total_tickets) as total_tickets,
    SUM(breached_tickets) as total_breached
FROM analytics_sla_metrics
GROUP BY category
ORDER BY avg_compliance_pct DESC;
```

---

### 9.3 Debug Mode

**Enable verbose logging:**

```python
# In config.py or airflow.env
LOG_LEVEL=DEBUG
```

**Check Airflow task logs:**

```bash
# View logs for specific task instance
docker exec -it <airflow-scheduler-container> \
  airflow tasks logs servicehub_etl extract_and_validate 2026-03-05
```

---

## Appendix A: Configuration

### Environment Variables

| Variable          | Description                  | Default         |
| ----------------- | ---------------------------- | --------------- |
| DB_HOST           | PostgreSQL host              | postgres        |
| DB_PORT           | PostgreSQL port              | 5432            |
| DB_NAME           | Database name                | servicehub      |
| DB_USER           | Database user                | servicehub      |
| DB_PASSWORD       | Database password            | (required)      |
| AIRFLOW_DB        | Airflow metadata DB          | airflow_metadata |
| LOG_LEVEL         | Logging level                | INFO            |
| APP_ENV           | Environment                  | development     |

---

## Appendix B: Contact

**Data Engineering Team:**
- Slack: #data-engineering
- Email: data-eng@servicehub.com
- On-call: PagerDuty rotation

**Related Documentation:**
- [Data Contract](../Data-Contract.md)
- [Backend API Documentation](../backend/README.md)
- [Dashboard User Guide](../docs/dashboard-guide.md)
