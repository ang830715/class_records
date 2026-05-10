# Class Records Deployment Runbook

This file records how the app was deployed to a CentOS 7 VPS and how to repeat the deployment later.

Current production-style setup after the BT Panel domain/SSL change:

```text
Browser
  -> https://physics.lyxi.top
  -> BT Panel Nginx serves React files from /www/wwwroot/physics.lyxi.top

Browser API calls
  -> https://physics.lyxi.top/api/...
  -> BT Panel Nginx reverse proxy sends /api to FastAPI on 127.0.0.1:8000
  -> FastAPI writes to PostgreSQL
```

Important: SSL is now handled by BT Panel. The app also has password login. Keep `/etc/class-records.env` private because it contains the auth secret and initial admin password.

Current auth implementation:

```text
POST /auth/login returns a signed bearer token.
The browser stores the token and sends Authorization: Bearer <token>.
Most API routes require that token.
```

## Server Facts

The first successful server was:

```text
OS: CentOS Linux release 7.9.2009
Nginx: BT Panel Nginx at /www/server/nginx/sbin/nginx, version 1.24.0
Public IP: 39.99.137.40
Domain: physics.lyxi.top
HTTPS: enabled by BT Panel
Backend service: class-records.service
Backend process: uvicorn on 127.0.0.1:8000
Python: /opt/class_records/py311/bin/python, version 3.11.15
```

Current deployed application state:

```text
Latest deployed commit: 1ab8c71 make AI schedule import work with provider
Backend health: http://127.0.0.1:8000/health returns {"status":"ok"}
AI timetable image import has worked once with the configured third-party provider.
Server Git working tree should be clean after pull; normal updates should use git pull --ff-only.
```

BT Panel manages the website entry:

```text
Site name: physics.lyxi.top
Site root: /www/wwwroot/physics.lyxi.top
SSL: enabled in BT Panel
```

BT Panel Nginx virtual host configs are included from:

```text
/www/server/panel/vhost/nginx/*.conf
```

Do not install another Nginx for this app. Use BT Panel's existing Nginx and configure the domain, SSL, static frontend root, and `/api` reverse proxy there.

## Project Changes Made For Deployment

The backend was updated so it can run behind Nginx at `/api`:

```text
ROOT_PATH=/api
CORS_ORIGINS=https://physics.lyxi.top
```

These deployment helper files were added:

```text
deploy/class-records.env.example
deploy/systemd/class-records.service
deploy/nginx/class-records.conf
deploy/README.md
```

Authentication/account files now include:

```text
backend/app/auth.py
backend/app/schema_management.py
backend/scripts/check_database.py
backend/scripts/set_admin_password.py
frontend/src/api.ts
frontend/src/main.tsx
```

## Server Directory Layout

The server uses these paths:

```text
/opt/class_records/app
  Git checkout of this project

/opt/class_records/py311
  Isolated Python 3.11 environment

/opt/class_records/miniforge
  Miniforge installer environment used to create Python 3.11

/var/www/class_records
  Old manual frontend folder from the first IP-based deployment

/www/wwwroot/physics.lyxi.top
  Current BT Panel site root for built React frontend files

/etc/class-records.env
  Backend environment variables

/etc/systemd/system/class-records.service
  systemd service for FastAPI
```

## Backend Environment File

The server file `/etc/class-records.env` should contain:

```text
DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
ROOT_PATH=/api
CORS_ORIGINS=https://physics.lyxi.top
AUTH_SECRET=replace-with-a-long-random-secret
INITIAL_ADMIN_EMAIL=teacher@example.com
INITIAL_ADMIN_PASSWORD=replace-with-a-strong-password
INITIAL_ADMIN_NAME=Teacher
AUTH_TOKEN_TTL_HOURS=168
AI_PROVIDER_BASE_URL=https://api.openai.com/v1
AI_PROVIDER_TOKEN=sk-your-provider-token
AI_SCHEDULE_MODEL=gpt-5.5
AI_SCHEDULE_API_STYLE=responses
AI_PROVIDER_USER_AGENT=class-records/0.1
```

If deploying somewhere else later, change `CORS_ORIGINS` to the real domain, for example:

```text
CORS_ORIGINS=https://classes.example.com
```

After changing `/etc/class-records.env`, restart the backend:

```bash
systemctl restart class-records
```

## First-Time Deployment

### 1. Install Python 3.11 On CentOS 7

CentOS 7 does not include Python 3.11. Do not replace the system Python because CentOS tools may depend on it.

Install an isolated Python with Miniforge:

```bash
mkdir -p /opt/class_records
cd /tmp
curl -L -o Miniforge3-Linux-x86_64.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p /opt/class_records/miniforge
/opt/class_records/miniforge/bin/conda create -y -p /opt/class_records/py311 python=3.11 pip
/opt/class_records/py311/bin/python --version
```

Expected:

```text
Python 3.11.x
```

If the server has a poor GitHub connection, download the Miniforge `.sh` file on your computer and upload it to `/tmp` with Xftp, then run:

```bash
bash /tmp/Miniforge3-Linux-x86_64.sh -b -p /opt/class_records/miniforge
```

### 2. Install PostgreSQL And Create The Database

Install PostgreSQL on the server, or use a managed PostgreSQL instance. If you use BT Panel, you can create the PostgreSQL database/user from the panel UI when the PostgreSQL service is installed.

Recommended database values:

```text
Database: class_records
User: class_records
Password: use a strong password
Host: 127.0.0.1
Port: 5432
```

Command-line example:

```bash
sudo -u postgres psql
CREATE USER class_records WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE class_records OWNER class_records;
\q
```

Verify the connection:

```bash
psql "postgresql://class_records:CHANGE_ME@127.0.0.1:5432/class_records" -c "select 1"
```

After backend dependencies are installed, you can also verify the app-level database setup:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/check_database.py
```

### 3. Clone The Project

```bash
id classrecords >/dev/null 2>&1 || useradd --system --home /opt/class_records --shell /sbin/nologin classrecords
mkdir -p /opt/class_records

if [ -d /opt/class_records/app/.git ]; then
  cd /opt/class_records/app && git pull --ff-only
else
  git clone https://github.com/ang830715/class_records.git /opt/class_records/app
fi
```

### 4. Install Backend Dependencies

```bash
cd /opt/class_records/app/backend
/opt/class_records/py311/bin/python -m pip install --upgrade pip
/opt/class_records/py311/bin/python -m pip install -r requirements.txt
```

On CentOS 7, `greenlet` may fail to build from source. If that happens:

```bash
/opt/class_records/miniforge/bin/conda install -y -p /opt/class_records/py311 -c conda-forge greenlet
cd /opt/class_records/app/backend
/opt/class_records/py311/bin/python -m pip install -r requirements.txt
```

### 5. Create Backend Env File

```bash
cp /opt/class_records/app/deploy/class-records.env.example /etc/class-records.env
vi /etc/class-records.env
```

For the current server, the file should be:

```text
DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
ROOT_PATH=/api
CORS_ORIGINS=https://physics.lyxi.top
AUTH_SECRET=replace-with-a-long-random-secret
INITIAL_ADMIN_EMAIL=teacher@example.com
INITIAL_ADMIN_PASSWORD=replace-with-a-strong-password
INITIAL_ADMIN_NAME=Teacher
AUTH_TOKEN_TTL_HOURS=168
AI_PROVIDER_BASE_URL=https://api.openai.com/v1
AI_PROVIDER_TOKEN=sk-your-provider-token
AI_SCHEDULE_MODEL=gpt-5.5
AI_SCHEDULE_API_STYLE=responses
AI_PROVIDER_USER_AGENT=class-records/0.1
```

Generate a strong `AUTH_SECRET` on the server with:

```bash
/opt/class_records/py311/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For timetable screenshot import, add your provider base URL and token to `/etc/class-records.env`. `AI_PROVIDER_BASE_URL` should normally include `/v1`. `AI_SCHEDULE_MODEL` is optional and defaults to `gpt-5.5`; change it if your provider uses a different model name. `AI_SCHEDULE_API_STYLE` can be `responses` or `chat_completions`. `AI_PROVIDER_USER_AGENT` defaults to `class-records/0.1`; some third-party providers reject Python's default user agent.

Current import behavior is strict. The provider must return a top-level `lessons` array with exact lesson objects: `weekday`, `period`, `start_time`, `end_time`, `duration_minutes`, `class_name`, `notes`, and `confidence`. The backend rejects aliases, extra keys, table-shaped output, weekday names, non-padded or invalid times, and durations that do not match the start/end time difference. Complete markdown JSON fences are stripped, but provider text around JSON is not recovered.

If you ever need to reset the app login:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/set_admin_password.py --email teacher@example.com
systemctl restart class-records
```

In `vi`:

```text
i       enter insert mode
Esc     leave insert mode
:wq     save and quit
```

### 6. Install And Start Backend Service

```bash
cp /opt/class_records/app/deploy/systemd/class-records.service /etc/systemd/system/class-records.service
systemctl daemon-reload
systemctl enable --now class-records
systemctl status class-records --no-pager
```

Test the backend on the server:

```bash
curl -s http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

### 7. Build Frontend On Local Computer

On the Windows computer, from PowerShell:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records\frontend"
$env:VITE_API_BASE="/api"
npm.cmd run build
```

This creates:

```text
C:\Users\Ang Li\Desktop\coding\class_records\frontend\dist
```

### 8. Upload Frontend Files

BT Panel created the website root here:

```text
/www/wwwroot/physics.lyxi.top
```

Upload the contents of `frontend/dist` into:

```text
/www/wwwroot/physics.lyxi.top
```

Important: upload the files inside `dist`, not the `dist` folder itself.

Correct final layout:

```text
/www/wwwroot/physics.lyxi.top/index.html
/www/wwwroot/physics.lyxi.top/assets/...
/www/wwwroot/physics.lyxi.top/manifest.webmanifest
```

Wrong layout:

```text
/www/wwwroot/physics.lyxi.top/dist/index.html
```

If the wrong layout happens, fix it on the server:

```bash
cp -r /www/wwwroot/physics.lyxi.top/dist/* /www/wwwroot/physics.lyxi.top/
chmod -R a+rX /www/wwwroot/physics.lyxi.top
```

### 9. Configure Reverse Proxy And SSL In BT Panel

BT Panel should manage the public website, SSL certificate, and reverse proxy.

In BT Panel:

```text
Website
  -> physics.lyxi.top
  -> Settings
  -> Reverse proxy
```

Create or verify a reverse proxy rule:

```text
Proxy path/prefix: /api
Target URL: http://127.0.0.1:8000
```

Conceptually, BT Panel should generate an Nginx rule equivalent to:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

SSL is also managed in BT Panel:

```text
Website
  -> physics.lyxi.top
  -> SSL
```

After changing BT Panel settings, test the current Nginx config if needed:

```bash
/www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
systemctl reload nginx
```

Open:

```text
https://physics.lyxi.top
```

Test API through Nginx:

```text
https://physics.lyxi.top/api/health
```

`/api/classes` and most other app routes now require login, so they should return `401` without a bearer token.

## Updating The App Later

When code changes are pushed to GitHub:

### 1. Pull New Code On Server

```bash
cd /opt/class_records/app
git status --short
git pull --ff-only
```

If `git pull --ff-only` says local changes would be overwritten, stop and inspect the files first. This happened once after live debugging `backend/app/schedule_import.py` directly on the server; the fix was to confirm the server file matched the pushed commit, make a backup copy under `/tmp`, restore the tracked file, and then pull.

### 2. Restart Backend If Backend Code Changed

```bash
cd /opt/class_records/app/backend
/opt/class_records/py311/bin/python scripts/check_database.py
systemctl restart class-records
systemctl status class-records --no-pager
```

### 3. Rebuild And Reupload Frontend If Frontend Code Changed

On local Windows:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records\frontend"
$env:VITE_API_BASE="/api"
npm.cmd run build
```

Then upload the contents of:

```text
frontend/dist
```

to:

```text
/www/wwwroot/physics.lyxi.top
```

After uploading, hard refresh the browser:

```text
Ctrl + F5
```

## Seeding The Real Weekly Schedule

The app includes a repeatable seed script for the real teaching timetable:

```text
backend/scripts/seed_schedule.py
```

It creates these classes if missing:

```text
3.5B, PA4, A2-4, PreDP4, A2-3, A2-1
```

It also creates or updates the Monday-Friday schedule rules. Running it more than once is safe; it updates existing matching rules instead of duplicating them.

Default behavior:

```text
active_from: 2026-01-01
duration_minutes: 45
```

Run locally against local SQLite:

```powershell
cd "C:\Users\Ang Li\Desktop\coding\class_records\backend"
$env:DATABASE_URL="sqlite:///./dev.db"
.\.venv\Scripts\python.exe scripts\seed_schedule.py
```

Run on the server against the deployed PostgreSQL database:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/check_database.py
/opt/class_records/py311/bin/python scripts/seed_schedule.py
systemctl restart class-records
```

If one period should count as 60 minutes instead of 45, run:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=postgresql+psycopg://class_records:CHANGE_ME@127.0.0.1:5432/class_records
/opt/class_records/py311/bin/python scripts/seed_schedule.py --duration-minutes 60
systemctl restart class-records
```

## Useful Commands

Backend service:

```bash
systemctl status class-records --no-pager
systemctl restart class-records
journalctl -u class-records -n 50 --no-pager
```

Backend direct tests:

```bash
curl -s http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/classes
```

Expected:

```text
/health returns 200 OK
/classes returns 401 Unauthorized unless you pass a bearer token
```

Schedule reset behavior:

```text
DELETE /schedule/{rule_id}
  Detaches old records from that schedule rule, then deletes the rule.

DELETE /schedule
  Clears all weekly schedule rules for the logged-in user.
  Existing class_records rows stay in the database.
```

Login test:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"teacher@example.com","password":"YOUR_PASSWORD"}'
```

Nginx tests:

```bash
/www/server/nginx/sbin/nginx -T | grep -n "include"
/www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
systemctl reload nginx
```

Frontend file checks:

```bash
ls -la /www/wwwroot/physics.lyxi.top
find /www/wwwroot/physics.lyxi.top -maxdepth 2 -type f | head -20
grep -R "localhost:8000\|/api" -n /www/wwwroot/physics.lyxi.top/assets/*.js | head
```

Database checks:

```bash
psql "postgresql://class_records:CHANGE_ME@127.0.0.1:5432/class_records" -c "select now()"
cd /opt/class_records/app/backend
/opt/class_records/py311/bin/python scripts/check_database.py
```

Disk checks:

```bash
df -h
df -i
du -sh /opt/* 2>/dev/null | sort -h
```

## Problems We Hit And Fixes

### Miniforge Installer Failed

Error:

```text
WARNING: md5sum mismatch of tar archive
critical libmamba Truncated tar archive detected
```

Cause: bad or partial download from GitHub.

Fix: download the `.sh` file on the local computer and upload it to the server with Xftp, then run it from `/tmp`.

### greenlet Failed To Build

Error:

```text
Failed building wheel for greenlet
```

Cause: CentOS 7 had trouble compiling the dependency from source.

Fix:

```bash
/opt/class_records/miniforge/bin/conda install -y -p /opt/class_records/py311 -c conda-forge greenlet
/opt/class_records/py311/bin/python -m pip install -r requirements.txt
```

### Backend Could Not Connect To PostgreSQL

Error:

```text
psycopg.OperationalError
```

Cause: database URL, credentials, or network access were wrong.

Fix: verify `DATABASE_URL` in `/etc/class-records.env`, check that PostgreSQL is running, and confirm the app database/user exists.

### Database Or Disk Is Full

Error:

```text
database or disk is full
```

Cause: server disk or PostgreSQL storage was full.

Fix: free disk space, then restart:

```bash
systemctl restart class-records
```

### Browser Showed 403 Forbidden

Cause: the uploaded frontend was in the wrong folder shape. `dist` was copied as a whole folder.

Wrong:

```text
/www/wwwroot/physics.lyxi.top/dist/index.html
```

Correct:

```text
/www/wwwroot/physics.lyxi.top/index.html
```

Fix:

```bash
cp -r /www/wwwroot/physics.lyxi.top/dist/* /www/wwwroot/physics.lyxi.top/
chmod -R a+rX /www/wwwroot/physics.lyxi.top
```

### API Worked Directly But Not Through Nginx Curl Test

This command may return 404:

```bash
curl -i http://127.0.0.1/api/health
```

But this is the real public test:

```text
https://physics.lyxi.top/api/health
```

Reason: Nginx chooses the server block by `server_name`. A request to `127.0.0.1` does not match the BT Panel site `physics.lyxi.top`.

Use this for browser-facing API tests:

```text
https://physics.lyxi.top/api/health
```

## Future Improvements

Before serious use:

```text
1. Keep HTTPS enabled in BT Panel.
2. Keep a strong AUTH_SECRET and admin password in /etc/class-records.env.
3. Add automatic backups for PostgreSQL.
4. Add Alembic migrations before larger schema changes.
5. Consider HttpOnly cookie sessions instead of localStorage bearer tokens.
6. Consider deploying on a newer OS than CentOS 7 later.
```

Simple PostgreSQL backup command:

```bash
mkdir -p /opt/class_records/backups
PGPASSWORD=CHANGE_ME pg_dump -h 127.0.0.1 -U class_records -d class_records > /opt/class_records/backups/prod-$(date +%F-%H%M%S).sql
```
