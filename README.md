# Teaching Records

A personal teaching record system for tracking the classes actually taught, comparing them with the planned schedule, and calculating reliable weekly/monthly/semester statistics for salary.

The key rule is simple: **`ClassRecord` is the source of truth**. Schedule rules describe what should happen; records describe what actually happened.

## Features

- Manage student groups and courses
- Define recurring weekly schedule rules
- Show today's expected classes dynamically
- Mark classes as taught or canceled from the Today page
- Add, edit, and delete actual class records manually
- Keep edit logs when class records are changed
- View weekly and monthly taught-class totals, hours, and salary
- Run as a web app suitable for Windows, macOS, and mobile browsers

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: PostgreSQL for normal deployment; SQLite is convenient for local development
- Frontend: React, TypeScript, Vite
- UI: plain CSS with lucide-react icons

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
3. Add a student group.
4. Add a course with a default rate.
5. Add a schedule rule for today's weekday.
6. Go to **Today**.
7. Mark the class as taught.
8. Go to **Stats** and check the weekly/monthly totals.
9. Go to **Records** and manually adjust the record if needed.

## Development Notes

- Generated schedule records are not stored in the database.
- `/today` merges dynamic schedule expectations with actual records.
- Salary is calculated only from taught `ClassRecord` rows.
- SQLite files such as `backend/dev.db` are local runtime data and ignored by Git.
- Build output such as `frontend/dist` is ignored by Git.

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
