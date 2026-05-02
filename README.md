# Teaching Records

A personal teaching record system for a physics teacher. It tracks the classes actually taught, compares them with the planned weekly schedule, and calculates reliable weekly/monthly/semester totals for salary checking.

The key rule is simple: **`ClassRecord` is the source of truth**. Schedule rules describe what should happen; records describe what actually happened.

## Features

- Manage teaching classes such as `PA4`
- Store each class's usual classroom and notes
- Define recurring weekly schedule rules by class, weekday, and time
- Show today's expected classes dynamically
- Mark classes as taught or canceled from the Today page
- Add, edit, and delete actual class records manually
- Keep edit logs when class records are changed
- View weekly and monthly taught-class totals and hours
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
    requirements.txt
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

