# Teaching Records

A personal teaching record system for a physics teacher. It tracks the classes actually taught, compares them with the planned weekly schedule, and calculates reliable weekly/monthly/semester totals for salary checking.

The key rule is simple: **`ClassRecord` is the source of truth**. Schedule rules describe what should happen; records describe what actually happened.

## Features

- Manage teaching classes such as `PA4`
- Store each class's usual classroom and notes
- Define recurring weekly schedule rules by class, weekday, and time
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
      database.py
      main.py
      models.py
      schemas.py
    scripts/
      seed_schedule.py
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

## Real Schedule Seed

The real weekly timetable can be inserted with:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./dev.db"
.\.venv\Scripts\python.exe scripts\seed_schedule.py
```

The seed script is safe to run more than once. It creates or updates the expected weekly lessons and does not duplicate matching rules.

On the deployed server, run:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/check_database.py
/opt/class_records/py311/bin/python scripts/seed_schedule.py
systemctl restart class-records
```

## Deployment Status

The first successful deployment uses:

```text
Domain: https://physics.lyxi.top
Frontend root: /www/wwwroot/physics.lyxi.top
Backend: FastAPI systemd service on 127.0.0.1:8000
Reverse proxy: BT Panel routes /api to the backend
Database: PostgreSQL
```

Detailed deployment notes and recovery commands are in:

```text
deploy/README.md
```

Important: the deployed app currently has HTTPS, but no login system yet.

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
- Salary/counting should be based only on `ClassRecord` rows.
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
python -m compileall backend\app
```

Stop local PostgreSQL:

```powershell
docker compose down
```

