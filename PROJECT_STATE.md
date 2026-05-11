# Project State

Last updated: 2026-05-11

This file is a handoff note for future conversations. It summarizes what has already been built and what assumptions are currently true.

## Product

Teaching Records is a personal teaching log for a physics teacher. The main rule is:

```text
ScheduleRule = expected weekly lesson
ClassRecord = actual class result and source of truth
Stats = derived from ClassRecord rows
```

Current frontend views:

```text
Today
Missing
Records
Stats
Schedule
Admin
Account
```

The Schedule view has an AI timetable image import workflow:

```text
Upload screenshot -> backend sends image to configured AI provider -> editable candidate rows -> user saves selected weekly lessons
```

The Schedule view also has a **Clear schedule** action:

```text
Clear schedule -> detach old records from their schedule_rule_id -> delete current user's ScheduleRule rows
```

Current status:

```text
Commit 20e7be0 is deployed on the server frontend only for paste-to-import.
Commit 4957f45 is committed and pushed to GitHub, but still needs backend/frontend deployment to the Aliyun server.
The server working tree was restored to normal git pull flow after earlier live hot-patches.
AI image upload has been tested once successfully with the user's third-party provider.
AI schedule import now uses strict schema validation.
Schedule clearing is deployed and preserves existing records.
```

## Current Architecture

Backend:

```text
FastAPI
SQLAlchemy
Pydantic
python-multipart for image uploads
```

Frontend:

```text
React
TypeScript
Vite
Plain CSS
lucide-react icons
```

Database:

```text
Production target: PostgreSQL
Local dev: SQLite via scripts/start-dev.ps1
```

Deployment:

```text
Domain: https://physics.lyxi.top
Server: Aliyun VPS, IP 39.99.137.40
Public web server: BT Panel Nginx
Frontend root: /www/wwwroot/physics.lyxi.top
Backend service: class-records.service
Backend bind: 127.0.0.1:8000
API public path: /api
Server app path: /opt/class_records/app
Python: /opt/class_records/py311/bin/python
Environment file: /etc/class-records.env
```

## Authentication

Authentication has been implemented.

Current style:

```text
Email/password login
Signed bearer token
Token stored in browser localStorage
Authorization: Bearer <token>
```

Backend files:

```text
backend/app/auth.py
backend/app/schema_management.py
backend/app/main.py
backend/app/models.py
backend/app/schemas.py
```

Important env vars:

```text
AUTH_SECRET
INITIAL_ADMIN_EMAIL
INITIAL_ADMIN_PASSWORD
INITIAL_ADMIN_NAME
AUTH_TOKEN_TTL_HOURS
AI_PROVIDER_BASE_URL
AI_PROVIDER_TOKEN
AI_SCHEDULE_MODEL
AI_SCHEDULE_API_STYLE
AI_PROVIDER_USER_AGENT
```

Public endpoints:

```text
GET /health
POST /auth/login
GET /auth/me if a valid token is present
```

Protected app endpoints include classes, schedule, records, today, stats, missing-days, semesters, account update, and password update.

Account page features:

```text
Update display name
Update email
Change password
Sign out
```

Admin page features:

```text
Create teacher accounts
List teacher accounts
Toggle active/admin access
Reset teacher passwords
```

Password reset helper:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/set_admin_password.py --email teacher@example.com
systemctl restart class-records
```

## Data Model Notes

Current relevant models:

```text
User
- id
- name
- email
- password_hash
- is_active
- created_at

TeachingClass
- user_id scoped

ScheduleRule
- user_id scoped

ClassRecord
- user_id scoped
- source of truth for actual lessons
- schedule_rule_id can become null when an old schedule is deleted or cleared

Semester
- user_id scoped
EditLog
```

AI schedule import does not add a database table. It returns candidate rows with weekday, period, start/end time, duration, class name, notes, and confidence. The frontend then creates missing `TeachingClass` rows and selected `ScheduleRule` rows through the normal API.

The current importer is strict:

```text
1. The provider/model must return the exact top-level lessons JSON schema.
2. The backend only performs minimal cleanup by removing complete markdown JSON fences.
3. Aliases such as schedule/classes, table-row output, day-grouped output, weekday names, non-padded times, extra keys, and computed durations are rejected.
4. duration_minutes must exactly match the difference between start_time and end_time.
```

The app bootstraps an initial admin account when the database is empty or when the configured initial admin email matches an existing user with no password yet.

Schedule reset behavior:

```text
DELETE /schedule/{rule_id} detaches matching ClassRecord.schedule_rule_id values before deleting the rule.
DELETE /schedule clears all current-user ScheduleRule rows and leaves ClassRecord rows intact.
```

## Runtime Schema

There are no Alembic migrations yet.

`backend/app/schema_management.py` exists to add the current auth columns to older databases at startup/check time:

```text
users.password_hash
users.is_active
users.is_admin
```

Future schema changes should probably introduce Alembic.

## Useful Local Commands

Start local dev:

```powershell
.\scripts\start-dev.ps1
```

Local dev login:

```text
Email: teacher@example.com
Password: teacher
```

Build frontend:

```powershell
cd frontend
npm.cmd run build
```

Compile backend:

```powershell
python -m compileall backend\app backend\scripts
```

Verify database:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./dev.db"
.\.venv\Scripts\python.exe scripts\check_database.py
```

Verify backend import after dependency changes:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./verify_import.db"
$env:AUTH_SECRET="verify-secret"
$env:INITIAL_ADMIN_EMAIL="teacher@example.com"
$env:INITIAL_ADMIN_PASSWORD="verify-password"
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title); print(len(app.routes))"
```

## Server Update Checklist

Backend update:

```bash
cd /opt/class_records/app
git pull --ff-only
cd /opt/class_records/app/backend
/opt/class_records/py311/bin/python -m pip install -r requirements.txt
/opt/class_records/py311/bin/python scripts/check_database.py
systemctl restart class-records
systemctl status class-records --no-pager
curl -s http://127.0.0.1:8000/health
```

Frontend update:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records\frontend"
$env:VITE_API_BASE="/api"
npm.cmd run build
npm.cmd is useful on Windows if npm.ps1 is blocked by execution policy.
```

Upload contents of:

```text
frontend/dist
```

to:

```text
/www/wwwroot/physics.lyxi.top
```

## Verification Notes

Recent local checks performed during implementation:

```text
PYTHONPYCACHEPREFIX=/private/tmp/class-records-pycache python3 -m compileall backend/app backend/scripts
npm run build
Python 3.13 temporary venv admin smoke test: first user is admin, admin can create teacher, deactivate/reactivate teacher, and reset teacher password.
HTTP smoke test: login, protected /classes, profile update, password change
Backend import smoke test for the image upload route
```

Expected protected-route behavior:

```text
GET /health -> 200
GET /classes without token -> 401
GET /classes with valid token -> 200
DELETE /schedule with valid token -> 204 and existing records remain
```

Current AI schedule import behavior:

```text
POST /schedule/import-image requires login.
If AI_PROVIDER_TOKEN/OPENAI_API_KEY is missing, it returns 503 with "Schedule image import is not configured".
The endpoint only returns preview candidates; it does not write schedule rows directly.
AI_PROVIDER_BASE_URL defaults to https://api.openai.com/v1.
AI_SCHEDULE_API_STYLE defaults to responses; use chat_completions for providers that only support /v1/chat/completions.
AI_PROVIDER_USER_AGENT defaults to class-records/0.1 to avoid providers rejecting Python's default user agent.
The provider response must validate against the strict ScheduleImportResult schema.
```

Recent server verification:

```text
Server repo: /opt/class_records/app
Latest backend deployed commit: 023be1d try fixing the delete schedule problem
Latest frontend uploaded change: paste-to-import screenshot bundle from commit 20e7be0
Backend service: active after restart
GET http://127.0.0.1:8000/health -> {"status":"ok"}
Public frontend/API remain behind https://physics.lyxi.top and /api
Frontend bundle deployed after paste-to-import: assets/index-BsC0fsE-.js
```

## Next Good Improvements

Recommended next work:

```text
1. Deploy the committed admin teacher-account management backend and frontend.
2. Add PostgreSQL automatic backups on the server.
3. Add Alembic migrations.
4. Add tests for auth, today, records, stats, and account changes.
5. Consider HttpOnly cookie sessions instead of localStorage bearer tokens.
6. Add schedule editing, not only schedule create/delete.
7. Add server-side bulk save/replace behavior for imported schedules if term schedule changes become frequent.
8. Consider one model-powered repair retry for AI import if strict provider output still fails occasionally.
```

## SSH Note

The user currently runs server commands manually over SSH. A future assistant can help over SSH once passwordless/unlocked key access works from local PowerShell:

```powershell
ssh root@39.99.137.40
```

Do not store or repeat SSH passphrases in project files or chat.

