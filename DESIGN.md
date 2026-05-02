# Teaching Record System - DESIGN.md

## 1. Project Overview

A personal-first teaching record system for a physics teacher.
Used for accurate tracking of actual classes taught and salary/count checking.

Supports:
- Daily class logging
- Schedule vs actual comparison
- Weekly/monthly/semester statistics
- Manual corrections with audit trail
- Multi-device usage through a web/PWA-style interface

Future: multi-user teachers.

---

## 2. Core Principles

### Source of Truth
ClassRecord is the only source of truth for what actually happened.

### Separation
- Schedule = expected
- Record = actual
- Stats = derived

### Daily Simplicity
The daily class information should match real life:
- class name, e.g. PA4
- classroom
- time
- notes

### Auditability
All record edits must be traceable.

### Simplicity
Monolithic backend, no microservices.

---

## 3. Tech Stack

Backend:
- FastAPI (Python)

Database:
- PostgreSQL for normal usage
- SQLite acceptable for local development

Frontend:
- React (Vite)

Architecture:
- Monolith REST API

---

## 4. Data Model

### User
- id
- name
- email
- created_at

---

### TeachingClass
- id
- name, e.g. PA4
- classroom
- notes

---

### ScheduleRule
- id
- user_id
- teaching_class_id
- weekday
- start_time
- duration_minutes
- active_from
- active_until
- is_active
- notes

---

### ClassRecord (CORE)
- id
- user_id
- schedule_rule_id (nullable)
- teaching_class_id
- classroom
- date
- start_time
- duration_minutes
- status:
  - taught
  - canceled
  - rescheduled
  - extra
  - pending
- fee_amount (optional, can stay 0 if salary is counted elsewhere)
- notes
- created_at
- updated_at

---

### Semester
- id
- name
- start_date
- end_date

---

### EditLog
- id
- record_id
- field_name
- old_value
- new_value
- edited_at

---

## 5. Key Logic

### Daily Generation
DO NOT store generated schedule records.
Generate expected classes dynamically.

### Missed Days Detection
Detect dates with schedule but no ClassRecord.

### Statistics
Based only on ClassRecord:
- taught class count
- canceled class count
- extra class count
- total teaching hours
- totals by class name

Salary can be derived later from ClassRecord if a rate model is added.

---

## 6. API Design

### Classes
GET /classes
POST /classes
PUT /classes/{id}
DELETE /classes/{id}

---

### Schedule
GET /schedule
POST /schedule
PUT /schedule/{id}
DELETE /schedule/{id}

---

### Records
GET /records
POST /records
PUT /records/{id}
DELETE /records/{id}

---

### Today
GET /today

Returns expected + actual merged.

---

### Stats
GET /stats?range=week
GET /stats?range=month
GET /stats?range=semester

---

## 7. Frontend Pages

### Today (MOST IMPORTANT)
- Show today's expected classes
- Display class name, classroom, time, notes
- Quick status buttons

---

### Records
- Table view
- Full edit/delete
- Manual correction of classroom, status, and notes

---

### Stats
- Weekly/monthly totals
- Totals grouped by class name

---

### Schedule
- Manage classes
- Manage recurring rules

---

## 8. Workflow

Daily:
1. Open app
2. Confirm classes
3. Done (<1 minute)

---

## 9. Edge Cases

- canceled classes
- makeup classes
- rescheduled classes
- missing logs
- manual edits
- classroom changes

---

## 10. Non-Goals

- microservices
- complex permissions
- real-time sync
- full school/student CRM

---

## 11. Success Criteria

- <1 min daily logging
- accurate taught class count
- easy correction
- low mental load during a teaching day
