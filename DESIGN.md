# Teaching Record System - DESIGN.md

## 1. Project Overview

A personal-first teaching record system for tracking actual classes taught.
Used for accurate salary calculation and statistics.

Supports:
- Daily class logging
- Schedule vs actual comparison
- Weekly/monthly/semester statistics
- Manual corrections with audit trail
- Multi-device usage (PWA)

Future: multi-user (teachers)

---

## 2. Core Principles

### Source of Truth
ClassRecord is the only source of truth.

### Separation
- Schedule = expected
- Record = actual
- Stats = derived

### Auditability
All edits must be traceable.

### Simplicity
Monolithic backend, no microservices.

---

## 3. Tech Stack

Backend:
- FastAPI (Python)

Database:
- PostgreSQL

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

### StudentGroup
- id
- name
- notes

---

### Course
- id
- name
- default_duration_minutes
- default_rate

---

### ScheduleRule
- id
- user_id
- student_group_id
- course_id
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
- student_group_id
- course_id
- date
- start_time
- duration_minutes
- status:
  - taught
  - canceled
  - rescheduled
  - extra
  - pending
- fee_amount
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

---

### Missed Days Detection
Detect dates with schedule but no ClassRecord.

---

### Salary
Based only on ClassRecord:

salary = sum(fee_amount where status == taught)

---

## 6. API Design

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
- Quick status buttons

---

### Records
- Table view
- Full edit/delete

---

### Stats
- Weekly/monthly totals
- Salary

---

### Schedule
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

---

## 10. Non-Goals

- microservices
- complex permissions
- real-time sync

---

## 11. Success Criteria

- <1 min daily logging
- accurate salary
- easy correction