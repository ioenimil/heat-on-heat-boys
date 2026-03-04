# ServiceHub Data Contract


## 1. Purpose & Scope

This document is the single authoritative reference for all data-related concerns in ServiceHub. It governs:

* The canonical database schema all teams build against
* Enum values and their exact string representations used in code
* SLA timing rules and how breach is computed
* Analytics tables the data engineering pipeline produces
* Field naming conventions that the backend API and Python ETL must honour
* Sample data volumes and generation rules

Any schema change — new column, renamed field, altered enum — requires the Data Engineer to update this document and notify all Backend Developers before merging.

---

# 2. Canonical Enum Values

All enums are stored as `VARCHAR` using the exact uppercase string values below. No integers, no abbreviations.

---

## 2.1 Request Category

| Value      | Description                                                           |
| ---------- | --------------------------------------------------------------------- |
| IT_SUPPORT | Any technology-related issue, software, network, accounts   |
| FACILITIES | Physical workspace, office equipment, cleaning, security |
| HR_REQUEST | People operations, leave, payroll, policy queries         |

---

## 2.2 Priority

| Value    | Description                                                                          |
| -------- | ------------------------------------------------------------------------------------ |
| CRITICAL | System outage or blocker affecting multiple staff — SLA countdown starts immediately |
| HIGH     | Single user severely impacted, work cannot proceed                                   |
| MEDIUM   | Degraded functionality, workaround exists                                            |
| LOW      | Cosmetic or informational request, no business impact                                |

---

## 2.3 Request Status

| Value       | Description                                                |
| ----------- | ---------------------------------------------------------- |
| OPEN        | Ticket created by employee, not yet routed to a department |
| ASSIGNED    | Auto-routed to department; agent allocated                 |
| IN_PROGRESS | Agent actively working on the request                      |
| RESOLVED    | Agent marks request complete; resolved_at timestamp set    |
| CLOSED      | Employee confirms resolution or auto-close after 72 hrs    |

---

## 2.4 User Role

| Value | Description                                                      |
| ----- | ---------------------------------------------------------------- |
| ADMIN | Full system access; manages users, departments, SLA policies     |
| AGENT | Handles assigned tickets; can transition status and add comments |
| USER  | Regular employee; can only see and manage their own tickets      |

---

# 3. Core Database Schema

PostgreSQL 16. All timestamps are `TIMESTAMPTZ` stored in UTC.
Primary keys are `UUID`.

---

## 3.1 users

| Column     | Type         | Nullable | Notes                                           |
| ---------- | ------------ | -------- | ----------------------------------------------- |
| id         | UUID PK      | NO       | Primary key                                     |
| email      | VARCHAR(255) | NO       | Unique. Used as login identifier                |
| password   | VARCHAR(255) | NO       | BCrypt hashed — never store plaintext           |
| full_name  | VARCHAR(255) | NO       | Display name shown in UI and tickets            |
| role       | VARCHAR(20)  | NO       | Enum | AGENT | USER                      |
| department | UUID FK → departments.id | YES      | FK reference |
| is_active  | BOOLEAN      | NO       | Default TRUE; soft-delete flag                  |
| created_at | TIMESTAMPTZ  | NO       | Set on INSERT via @PrePersist                   |
| updated_at | TIMESTAMPTZ  | NO       | Set on INSERT and UPDATE                        |

---

## 3.2 departments

| Column        | Type         | Nullable | Notes                                            |
| ------------- | ------------ | -------- | ------------------------------------------------ |
| id            | UUID PK      | NO       | Primary key                                      |
| name          | VARCHAR(100) | NO       | Human-readable Support', 'HR', 'Facilities' |
| category      | VARCHAR(20)  | NO       | Enum | FACILITIES | HR_REQUEST       |
| contact_email | VARCHAR(255) | YES      | Routing email for notifications   |
| is_active     | BOOLEAN      | NO       | Default TRUE                                     |

One department row per RequestCategory.
The auto-routing logic maps `category → department` by this column.

---

## 3.3 service_requests

| Column            | Type                     | Nullable | Notes                                                                     |
| ----------------- | ------------------------ | -------- | ------------------------------------------------------------------------- |
| id                | UUID PK                  | NO       | Primary key                                                               |
| title             | VARCHAR(255)             | NO       | Short summary of the request                                              |
| description       | TEXT                     | YES      | Full detail provided by the requester                                     |
| category          | VARCHAR(20)              | NO       | Enum | FACILITIES | HR_REQUEST                                |
| priority          | VARCHAR(10)              | NO       | Enum | HIGH | MEDIUM | LOW                                      |
| status            | VARCHAR(15)              | NO       | Enum | ASSIGNED | IN_PROGRESS | RESOLVED | CLOSED                   |
| department_id     | UUID FK → departments.id | YES      | Set by auto-routing on creation                                           |
| assigned_to_id    | UUID FK → users.id       | YES      | Set when status → ASSIGNED                                                |
| requester_id      | UUID FK → users.id       | NO       | The employee who raised the ticket                                        |
| sla_deadline      | TIMESTAMPTZ              | YES      | Calculated as created_at + resolution_hours from sla_policies               |
| first_response_at | TIMESTAMPTZ              | YES      | Timestamp of first status change away from OPEN                           |
| resolved_at       | TIMESTAMPTZ              | YES      | Set when status → RESOLVED                                                |
| closed_at         | TIMESTAMPTZ              | YES      | Set when status → CLOSED                                                  |
| is_sla_breached   | BOOLEAN                  | NO       | Default FALSE; set TRUE when NOW() > sla_deadline and not RESOLVED/CLOSED |
| created_at        | TIMESTAMPTZ              | NO       | Set on INSERT                                                             |
| updated_at        | TIMESTAMPTZ              | NO       | Set on every UPDATE                                                       |

---

## 3.4 sla_policies

| Column                | Type        | Nullable | Notes                                      |
| --------------------- | ----------- | -------- | ------------------------------------------ |
| id                    | UUID PK     | NO       | Primary key                                |
| category              | VARCHAR(20) | NO       | Enum | FACILITIES | HR_REQUEST |
| priority              | VARCHAR(10) | NO       | Enum | HIGH | MEDIUM | LOW       |
| response_time_hours   | INTEGER     | NO       | Max hours to first agent response          |
| resolution_time_hours | INTEGER     | NO       | Max hours from creation to RESOLVED        |

Unique constraint on `(category, priority)`.

---


# 4. SLA Policy Reference


| Category   | Priority | Response (hrs) | Resolution (hrs) | SLA Deadline = created_at + |
| ---------- | -------- | -------------- | ---------------- | --------------------------- |
| IT_SUPPORT | CRITICAL | 1              | 4                | created_at + 4 hrs          |
| IT_SUPPORT | HIGH     | 2              | 8                | created_at + 8 hrs          |
| IT_SUPPORT | MEDIUM   | 4              | 24               | created_at + 24 hrs         |
| IT_SUPPORT | LOW      | 8              | 72               | created_at + 72 hrs         |
| FACILITIES | CRITICAL | 1              | 8                | created_at + 8 hrs          |
| FACILITIES | HIGH     | 2              | 16               | created_at + 16 hrs         |
| FACILITIES | MEDIUM   | 4              | 48               | created_at + 48 hrs         |
| FACILITIES | LOW      | 8              | 96               | created_at + 96 hrs         |
| HR_REQUEST | CRITICAL | 2              | 8                | created_at + 8 hrs          |
| HR_REQUEST | HIGH     | 4              | 24               | created_at + 24 hrs         |
| HR_REQUEST | MEDIUM   | 8              | 72               | created_at + 72 hrs         |
| HR_REQUEST | LOW      | 24             | 168              | created_at + 168 hrs        |

---

## 4.1 SLA Calculation Rules

* `sla_deadline = created_at + resolution_time_hours`
* `is_sla_breached = TRUE when NOW() > sla_deadline AND status NOT IN ('RESOLVED','CLOSED')`
* Response SLA breach = `first_response_at IS NULL AND NOW() > created_at + response_time_hours`
* All timestamps use UTC
* Business hours are NOT factored in

SLA compliance rate:

```
(tickets resolved before sla_deadline) / (total resolved tickets) × 100
```

Grouped by category and priority.

---

# 5. Analytics Tables (Data Engineering Outputs)

---

## 5.1 analytics_sla_metrics

Granularity row per `(category, priority)`

| Column               | Type         | Description                                     |
| -------------------- | ------------ | ----------------------------------------------- |
| category             | VARCHAR(20)  | IT_SUPPORT | FACILITIES | HR_REQUEST            |
| priority             | VARCHAR(10)  | CRITICAL | HIGH | MEDIUM | LOW                  |
| total_tickets        | INTEGER      | Count of all tickets ever for this combination  |
| resolved_tickets     | INTEGER      | Count with status RESOLVED or CLOSED            |
| breached_tickets     | INTEGER      | Count where is_sla_breached = TRUE              |
| compliance_rate_pct  | NUMERIC(5,2) | resolved_within_sla / resolved_tickets × 100    |
| avg_resolution_hours | NUMERIC(8,2) | Mean hours from created_at to resolved_at       |
| avg_response_hours   | NUMERIC(8,2) | Mean hours from created_at to first_response_at |
| last_updated_at           | TIMESTAMPTZ  | When this row was last computed                 |

---

## 5.2 analytics_daily_volume

| Column       | Type        | Description                   |
| ------------ | ----------- | ----------------------------- |
| report_date  | DATE        | The calendar day (UTC)        |
| category     | VARCHAR(20) | Request category              |
| priority     | VARCHAR(10) | Request priority              |
| status       | VARCHAR(15) | Status at end of day snapshot |
| ticket_count | INTEGER     | Tickets opened on this date   |
| last_updated_at   | TIMESTAMPTZ | When this row was last computed                 |

---

## 5.3 analytics_agent_performance

Granularity row per agent per week.

| Column                  | Type         | Description                    |
| ----------------------- | ------------ | ------------------------------ |
| agent_id                | UUID         | FK reference to users.id       |
| agent_name              | VARCHAR(255) | Denormalised                   |
| week_start              | DATE         | Monday of ISO week             |
| tickets_assigned        | INTEGER      | Tickets assigned               |
| tickets_resolved        | INTEGER      | Tickets resolved               |
| avg_resolution_hours    | NUMERIC(8,2) | Mean resolution time           |
| sla_compliance_rate_pct | NUMERIC(5,2) | Percentage resolved within SLA |
| last_updated_at                 | TIMESTAMPTZ  | When last computed                  |

---

## 5.4 analytics_department_workload

| Column               | Type         | Description                    |
| -------------------- | ------------ | ------------------------------ |
| department_id        | UUID         | FK reference to departments.id |
| department_name      | VARCHAR(100) | Denormalised                   |
| week_start           | DATE         | Monday of ISO week             |
| open_tickets         | INTEGER      | Count OPEN or ASSIGNED         |
| resolved_tickets     | INTEGER      | Count resolved                 |
| breached_tickets     | INTEGER      | Count breached                 |
| avg_resolution_hours | NUMERIC(8,2) | Mean resolution hours          |
| last_updated_at           | TIMESTAMPTZ  | When last computed                  |

---

# 6. Sample Data Generation Specification

The Data Engineer is responsible for generating the seed data below so all dashboards are populated during demos.

Generated with **Python (Faker + random)**.

---

## 6.1 Volume Requirements

| Entity        | Count | Notes                                                               |
| ------------- | ----- | ------------------------------------------------------------------- |
| Users (AGENT) | 5     | Distributed across IT Support, HR, and Facilities departments       |
| Users (USER)  | 20    | Regular employees submitting requests                               |
| Tickets       | 200   | Spread across 60 days; all categories, all priorities, all statuses |

---

## 6.2 Ticket Distribution

| Dimension  | Distribution                                                                       |
| ---------- | ---------------------------------------------------------------------------------- |
| Category   | IT_SUPPORT 50% | FACILITIES 25% | HR_REQUEST 25%                                   |
| Priority   | CRITICAL 10% | HIGH 25% | MEDIUM 45% | LOW 20%                                     |
| Status     | OPEN 15% | ASSIGNED 10% | IN_PROGRESS 20% | RESOLVED 40% | CLOSED 15%              |
| Date range | `created_at` spread uniformly over last 60 days                                    |
| SLA breach | ~15% of resolved tickets should have `is_sla_breached = TRUE` for realistic charts |

---

# 7. Field Naming Conventions

Consistent naming prevents silent mapping bugs between Python and Java. These rules are mandatory.

| Layer           | Convention       | Example                                           |
| --------------- | ---------------- | ------------------------------------------------- |
| PostgreSQL      | snake_case       | `created_at`, `department_id`, `is_sla_breached`  |
| Java / JPA      | camelCase        | `createdAt`, `departmentId`, `isSlaBreached`      |
| Python / Pandas | snake_case       | `created_at`, `department_id` (matches DB)        |
| JSON API        | camelCase        | `createdAt`, `departmentName` (Jackson default)   |
| Enum in DB      | UPPER_SNAKE_CASE | `IT_SUPPORT`, `IN_PROGRESS`, `HR_REQUEST`         |
| Boolean columns | `is_` prefix     | `is_active`, `is_sla_breached`                    |
| FK columns      | `_id` suffix     | `requester_id`, `assigned_to_id`, `department_id` |
| Timestamp cols  | `_at` suffix     | `created_at`, `resolved_at`, `first_response_at`  |

---

# 8. ETL Pipeline Interface

Defines what the Python ETL reads, transforms, and writes.

Backend developers must not drop or rename source tables/columns without coordinating with the Data Engineer.

---

## 8.1 Source Tables (Read-Only for ETL)

* `service_requests` — primary source for all metrics
* `users` — needed for `agent_name` denormalisation
* `departments` — needed for `department_name` denormalisation
* `sla_policies` — needed to compute compliance (`resolution_time_hours`)

---

## 8.2 Output Tables (Written by ETL, Read by Backend)

* `analytics_sla_metrics` — refreshed on every run (**REPLACE strategy**)
* `analytics_daily_volume` — refreshed on every run (**REPLACE strategy**)
* `analytics_agent_performance` — refreshed on every run (**REPLACE strategy**)
* `analytics_department_workload` — refreshed on every run (**REPLACE strategy**)

The backend `DashboardService` must query `analytics_*` tables, not recompute metrics itself.

---

# 9. Status Workflow & Timestamp Rules

The Data Engineer depends on these transitions being enforced correctly to produce accurate metrics.

Backend developers must follow these rules exactly.

| Transition             | Who triggers it                 | Columns updated                             |
| ---------------------- | ------------------------------- | ------------------------------------------- |
| OPEN → ASSIGNED        | System (auto-route on creation) | `assigned_to_id`, `department_id`, `status` |
| ASSIGNED → IN_PROGRESS | AGENT                           | `status`, `updated_at`                      |
| IN_PROGRESS → RESOLVED | AGENT                           | `status`, `resolved_at`, `updated_at`       |
| RESOLVED → CLOSED      | USER or auto (72 hrs)           | `status`, `closed_at`, `updated_at`         |

