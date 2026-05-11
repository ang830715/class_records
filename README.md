# Teaching Records

A personal teaching record system for a physics teacher. It tracks the classes actually taught, compares them with the planned weekly schedule, and calculates reliable weekly/monthly/semester totals for salary checking.

The key rule is simple: **`ClassRecord` is the source of truth**. Schedule rules describe what should happen; records describe what actually happened.

## Features

- Password login with signed bearer tokens
- Admin-only teacher account creation and password reset
- Account page for updating display name, email, and password
- Manage teaching classes such as `PA4`
- Store each class's usual classroom and notes
- Define recurring weekly schedule rules by class, weekday, and time
- Clear all weekly schedule rules without deleting existing class records
- Import a timetable screenshot with AI and review the extracted weekly lessons before saving
- Show a daily teaching checklist from the weekly schedule
- Show the selected date and weekday clearly in English
- Show period labels such as `P1` and `P2` together with start times
- Mark single classes as taught or canceled from the Today page
- Mark all scheduled classes as taught for a normal teaching day
- Cancel all scheduled classes for a holiday or school event day
- Add, edit, and delete actual class records manually
- Filter records by salary-period date range, class, and status
- Keep edit logs when class records are changed
- View weekly, monthly, salary-period, and custom-range taught-class totals and hours
- Run as a web app suitable for Windows, macOS, and mobile browsers

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: PostgreSQL for normal deployment; SQLite is convenient for local development
- Frontend: React, TypeScript, Vite
- UI: plain CSS with lucide-react icons
- Authentication: password hash stored on `User`, signed bearer token from `AUTH_SECRET`
- AI schedule import: backend sends timetable images to a configured OpenAI-compatible provider

## Current State

As of the latest local work:

- Production is intended to use PostgreSQL.
- Local development uses SQLite through `scripts/start-dev.ps1`.
- App routes are protected by login except `/health`, `/auth/login`, and `/auth/me` when checking an existing token.
- The frontend includes **Today**, **Missing**, **Records**, **Stats**, **Schedule**, **Admin**, and **Account** views.
- The Schedule page includes AI timetable screenshot import by file upload or pasted screenshot. It has been tested successfully once on production with the configured third-party provider.
- The Admin page creates teacher accounts, toggles active/admin access, and resets teacher passwords.
- `TeachingClass`, `ScheduleRule`, `ClassRecord`, and `Semester` are now teacher-owned.
- There are no Alembic migrations yet. `backend/app/schema_management.py` contains a small runtime compatibility helper for the new auth columns.
- The latest high-level handoff is in `PROJECT_STATE.md`.

## Core Data Model

```text
TeachingClass
- name          example: PA4
- classroom     example: Room 302
- notes

ScheduleRule
- teaching_class_id
- weekday
- start_time
- duration_minutes
- active_from / active_until
- notes

ClassRecord
- teaching_class_id
- classroom     actual classroom snapshot
- date
- start_time
- duration_minutes
- status        taught / canceled / rescheduled / extra / pending
- notes
```

## Project Structure

```text
class_records/
  backend/
    app/
      auth.py
      database.py
      main.py
      models.py
      schema_management.py
      schemas.py
    scripts/
      check_database.py
      set_admin_password.py
    requirements.txt
  deploy/
    README.md
    class-records.env.example
    nginx/
    systemd/
  frontend/
    src/
      api.ts
      main.tsx
      styles.css
      types.ts
    package.json
  docker-compose.yml
  DESIGN.md
  PROJECT_STATE.md
  README.md
```

## Prerequisites

- Python 3.11+
- Node.js LTS or newer
- Docker Desktop, only if using PostgreSQL locally

On Windows PowerShell, if `npm` is blocked by execution policy, use `npm.cmd`.


## One-Command Local Run

From the project root, start the SQLite database file, backend, and frontend dev server with:

```powershell
.\scripts\start-dev.ps1
```

Then open:

```text
http://localhost:5173
```

Stop the dev servers with:

```powershell
.\scripts\stop-dev.ps1
```

Logs are written to `.dev-logs/`.

## Current Workflow

The app is built around the difference between expected classes and actual records:

```text
ScheduleRule = expected weekly lesson
ClassRecord = actual class result
Stats = calculated from ClassRecord rows
```

Typical daily use:

1. Open **Today**.
2. Check the date and weekday.
3. If the day happened normally, use **Mark all taught**.
4. If the whole day was canceled, use **Cancel day**.
5. If only one class changed, use the row-level taught/canceled buttons.
6. Use **Records** later to find and correct individual records.

Salary checking:

1. Open **Stats**.
2. Use **Salary** for the normal 15th-to-15th period.
3. Use **Custom** if the school asks for a different start/end date.

Schedule setup:

1. Add reusable class names in **Schedule** with **Add class**.
2. Add recurring weekly lessons in **Add weekly lesson**.
3. Use `P1`, `P2`, etc. in **Period / notes** when the note is a period label.
4. Or use **Import timetable image** to upload a screenshot, review the AI-extracted rows, and save selected weekly lessons.
5. Use **Clear schedule** when you need to reset the weekly timetable. Existing records stay in **Records**.

Current AI import note:

```text
The importer now uses a strict JSON contract. The provider must return exactly {"lessons":[...]} with the required lesson fields; the backend only strips optional markdown fences before JSON parsing and rejects aliases, extra keys, loose weekday names, loose times, and mismatched durations.
```

Account management:

1. Open **Account** after signing in.
2. Update your display name or email.
3. Change your password by entering the current password and the new password.

Authentication notes:

```text
POST /auth/login    returns a signed bearer token
GET /auth/me        returns the logged-in user
PUT /auth/me        updates display name and email
PUT /auth/password  changes password
GET /admin/users    lists teacher accounts for admins
POST /admin/users   creates teacher accounts for admins
```

The token is stored in browser `localStorage` by the current frontend. This is a simple first auth layer; a future hardening step would be HttpOnly cookie sessions.

## Deployment Status

The first successful deployment uses:

```text
Domain: https://physics.lyxi.top
Frontend root: /www/wwwroot/physics.lyxi.top
Backend: FastAPI systemd service on 127.0.0.1:8000
Reverse proxy: BT Panel routes /api to the backend
Database: PostgreSQL
```

Current deployed application commit:

```text
023be1d try fixing the delete schedule problem
```

The server working tree is expected to stay clean so normal `git pull --ff-only` works. Avoid live-editing server files except during emergency debugging; make local commits and deploy them through Git when possible.

Detailed deployment notes and recovery commands are in:

```text
deploy/README.md
```

Important: the deployed app has app-level login. Keep `AUTH_SECRET` and `INITIAL_ADMIN_PASSWORD` private.

## Quick Start With SQLite

This is the easiest way to develop and test the app locally.

From the project root:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records"
```

Create and prepare the backend environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the backend:

```powershell
$env:DATABASE_URL="sqlite:///./dev.db"
$env:AUTH_SECRET="local-dev-secret-change-me"
$env:INITIAL_ADMIN_EMAIL="teacher@example.com"
$env:INITIAL_ADMIN_PASSWORD="teacher"
$env:INITIAL_ADMIN_NAME="Teacher"
$env:AI_PROVIDER_BASE_URL="https://api.openai.com/v1"
$env:AI_PROVIDER_TOKEN="sk-your-provider-token"  # optional, only needed for timetable image import
$env:AI_SCHEDULE_MODEL="gpt-5.5"
$env:AI_SCHEDULE_API_STYLE="responses"
$env:AI_PROVIDER_USER_AGENT="class-records/0.1"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second terminal, start the frontend:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records\frontend"
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:5173
```

Default local development login from the commands above or `scripts/start-dev.ps1`:

```text
Email: teacher@example.com
Password: teacher
```

Reset the admin login if needed:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./dev.db"
.\.venv\Scripts\python.exe scripts\set_admin_password.py --email teacher@example.com
```

API docs:

```text
http://localhost:8000/docs
```

## PostgreSQL Mode

Start PostgreSQL from the project root:

```powershell
docker compose up -d
```

Then start the backend with the default PostgreSQL connection:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The default backend database URL is:

```text
postgresql+psycopg://class_records:class_records@localhost:5432/class_records
```

You can override it with:

```powershell
$env:DATABASE_URL="your_database_url_here"
```

## First Manual Test

1. Open the app.
2. Go to **Schedule**.
3. Add a class, for example `PA4`.
4. Add its classroom, for example `Room 302`.
5. Add a schedule rule for today's weekday and time.
6. Go to **Today**.
7. Mark the class as taught.
8. Go to **Stats** and check the weekly/monthly totals.
9. Go to **Records** and manually adjust classroom, status, or notes if needed.

## Development Notes

- Generated schedule records are not stored in the database.
- `/today` merges dynamic schedule expectations with actual records.
- Deleting one schedule rule or clearing all schedule rules sets old records' `schedule_rule_id` to null instead of deleting the records.
- Salary/counting should be based only on `ClassRecord` rows.
- Most app API routes use the logged-in `current_user.id`; the frontend should not send or choose `user_id`.
- `POST /schedule/import-image` requires login and `AI_PROVIDER_TOKEN`; it returns editable schedule candidates and does not write to the database by itself.
- `AI_PROVIDER_BASE_URL` should normally include `/v1`. `AI_SCHEDULE_API_STYLE` can be `responses` or `chat_completions`, depending on what the provider supports.
- `AI_PROVIDER_USER_AGENT` defaults to `class-records/0.1`; some third-party providers reject Python's default user agent.
- The current importer is strict: it requires a top-level `lessons` array, exact lesson keys, integer weekday values from 0 to 6, zero-padded real `HH:MM` times, and `duration_minutes` matching the start/end time difference.
- SQLite files such as `backend/dev.db` are local runtime data and ignored by Git.
- Build output such as `frontend/dist` is ignored by Git.
- Production deployment should use PostgreSQL; SQLite is only for local development.
- This early version does not include migrations yet. If you changed schemas while using SQLite, remove `backend/dev.db` and restart the backend.

## Useful Commands

Build the frontend:

```powershell
cd frontend
npm.cmd run build
```

Check backend Python syntax:

```powershell
python -m compileall backend\app backend\scripts
```

Stop local PostgreSQL:

```powershell
docker compose down
```

