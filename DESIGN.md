# Teaching Record System - DESIGN.md

## 1. Project Overview

A personal-first teaching record system for a physics teacher.
Used for accurate tracking of actual classes taught and salary/count checking.

Supports:
- Daily class logging
- Schedule vs actual comparison
- Weekly/monthly/semester statistics
- Manual corrections with audit trail
- Password login
- Account profile and password updates
- AI-assisted timetable screenshot import
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

### Authentication Boundary
The browser must authenticate before reading or changing app data. Backend routes should derive the active teacher from `current_user.id`, not from client-supplied `user_id`.

### Simplicity
Monolithic backend, no microservices.

---

## 3. Tech Stack

Backend:
- FastAPI (Python)

Database:
- PostgreSQL for normal usage and production
- SQLite acceptable for local development only
- Production should stay on PostgreSQL so future multi-user support can rely on proper concurrent access, backups, and operational tooling

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
- password_hash
- is_active
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

### Authentication
- `POST /auth/login` verifies email/password and returns a signed bearer token.
- Tokens are signed with `AUTH_SECRET` and expire according to `AUTH_TOKEN_TTL_HOURS`.
- Passwords are stored as PBKDF2-SHA256 hashes.
- The first admin user is initialized from `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`, and `INITIAL_ADMIN_NAME`.
- `PUT /auth/me` updates name/email.
- `PUT /auth/password` changes the current user's password after checking the current password.

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

### Auth / Account
POST /auth/login
GET /auth/me
PUT /auth/me
PUT /auth/password

---

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
POST /schedule/import-image

All schedule routes are scoped by the logged-in user's id.
`POST /schedule/import-image` sends an uploaded timetable image to the configured AI provider and returns candidate lessons for frontend review. It does not save rules directly.

---

### Records
GET /records
POST /records
PUT /records/{id}
DELETE /records/{id}

All record routes are scoped by the logged-in user's id.

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
- Import a timetable screenshot, review extracted rows, then save selected rules

---

### Account
- View signed-in user
- Update display name
- Update email
- Change password
- Sign out

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
- complex permissions in the current single-teacher release
- real-time sync
- full school/student CRM

---

## 11. Current Technical Notes

- Production database target is PostgreSQL.
- Local development can use SQLite.
- AI schedule import requires `AI_PROVIDER_TOKEN`; `AI_PROVIDER_BASE_URL` points to an OpenAI-compatible `/v1` base URL.
- `AI_SCHEDULE_API_STYLE` can be `responses` or `chat_completions`; `AI_SCHEDULE_MODEL` defaults to `gpt-5.5`.
- Provider calls include `AI_PROVIDER_USER_AGENT`, defaulting to `class-records/0.1`, because some third-party providers reject Python's default user agent.
- No Alembic migrations are present yet.
- `backend/app/schema_management.py` currently handles runtime addition of auth columns for older databases.
- `TeachingClass` is still global, while `ScheduleRule` and `ClassRecord` are user-scoped.
- True multi-user support should decide whether classes remain shared or become per-user.

---

## 12. Success Criteria

- <1 min daily logging
- accurate taught class count
- easy correction
- low mental load during a teaching day
- login protects production data
- account changes can be done from the web UI

