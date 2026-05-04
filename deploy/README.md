# Class Records Deployment Runbook

This file records how the app was deployed to a CentOS 7 VPS and how to repeat the deployment later.

Current production-style setup:

```text
Browser
  -> http://39.99.137.40
  -> Nginx serves React files from /var/www/class_records

Browser API calls
  -> http://39.99.137.40/api/...
  -> Nginx proxies to FastAPI on 127.0.0.1:8000
  -> FastAPI writes to SQLite at /opt/class_records/data/prod.db
```

Important: this app currently has no login. Anyone who can access the IP can edit the records. Add HTTPS and access protection before using it for sensitive data.

## Server Facts

The first successful server was:

```text
OS: CentOS Linux release 7.9.2009
Nginx: /www/server/nginx/sbin/nginx, version 1.24.0
Public IP: 39.99.137.40
Backend service: class-records.service
Backend process: uvicorn on 127.0.0.1:8000
Python: /opt/class_records/py311/bin/python, version 3.11.15
```

Nginx virtual host configs are included from:

```text
/www/server/panel/vhost/nginx/*.conf
```

The actual deployed Nginx config file is:

```text
/www/server/panel/vhost/nginx/class_records.conf
```

## Project Changes Made For Deployment

The backend was updated so it can run behind Nginx at `/api`:

```text
ROOT_PATH=/api
CORS_ORIGINS=http://39.99.137.40
```

These deployment helper files were added:

```text
deploy/class-records.env.example
deploy/systemd/class-records.service
deploy/nginx/class-records.conf
deploy/README.md
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

/opt/class_records/data
  Persistent app data

/opt/class_records/data/prod.db
  SQLite production database

/var/www/class_records
  Built React frontend files served by Nginx

/etc/class-records.env
  Backend environment variables

/etc/systemd/system/class-records.service
  systemd service for FastAPI
```

## Backend Environment File

The server file `/etc/class-records.env` should contain:

```text
DATABASE_URL=sqlite:////opt/class_records/data/prod.db
ROOT_PATH=/api
CORS_ORIGINS=http://39.99.137.40
```

If deploying to a domain later, change `CORS_ORIGINS` to the real domain, for example:

```text
CORS_ORIGINS=https://classes.example.com
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

### 2. Clone The Project

```bash
id classrecords >/dev/null 2>&1 || useradd --system --home /opt/class_records --shell /sbin/nologin classrecords
mkdir -p /opt/class_records

if [ -d /opt/class_records/app/.git ]; then
  cd /opt/class_records/app && git pull --ff-only
else
  git clone https://github.com/ang830715/class_records.git /opt/class_records/app
fi
```

### 3. Install Backend Dependencies

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

### 4. Prepare Data Directory

The SQLite database should live outside the source code checkout:

```bash
mkdir -p /opt/class_records/data
chown -R classrecords:classrecords /opt/class_records/data
```

### 5. Create Backend Env File

```bash
cp /opt/class_records/app/deploy/class-records.env.example /etc/class-records.env
vi /etc/class-records.env
```

For the current server, the file should be:

```text
DATABASE_URL=sqlite:////opt/class_records/data/prod.db
ROOT_PATH=/api
CORS_ORIGINS=http://39.99.137.40
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

Create the server folder:

```bash
mkdir -p /var/www/class_records
```

Upload the contents of `frontend/dist` into:

```text
/var/www/class_records
```

Important: upload the files inside `dist`, not the `dist` folder itself.

Correct final layout:

```text
/var/www/class_records/index.html
/var/www/class_records/assets/...
/var/www/class_records/manifest.webmanifest
```

Wrong layout:

```text
/var/www/class_records/dist/index.html
```

If the wrong layout happens, fix it on the server:

```bash
cp -r /var/www/class_records/dist/* /var/www/class_records/
chmod -R a+rX /var/www/class_records
```

### 9. Configure Nginx

Create this file on the server:

```text
/www/server/panel/vhost/nginx/class_records.conf
```

Content for the current IP:

```nginx
server {
    listen 80;
    server_name 39.99.137.40;

    root /var/www/class_records;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Test and reload Nginx:

```bash
/www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
systemctl reload nginx
```

Open:

```text
http://39.99.137.40
```

Test API through Nginx:

```text
http://39.99.137.40/api/health
http://39.99.137.40/api/classes
```

## Updating The App Later

When code changes are pushed to GitHub:

### 1. Pull New Code On Server

```bash
cd /opt/class_records/app
git pull --ff-only
```

### 2. Restart Backend If Backend Code Changed

```bash
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
/var/www/class_records
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

Run on the server against the deployed SQLite database:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=sqlite:////opt/class_records/data/prod.db
/opt/class_records/py311/bin/python scripts/seed_schedule.py
systemctl restart class-records
```

If one period should count as 60 minutes instead of 45, run:

```bash
cd /opt/class_records/app/backend
export DATABASE_URL=sqlite:////opt/class_records/data/prod.db
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
curl -s http://127.0.0.1:8000/classes
```

Nginx tests:

```bash
/www/server/nginx/sbin/nginx -T | grep -n "include"
/www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
systemctl reload nginx
```

Frontend file checks:

```bash
ls -la /var/www/class_records
find /var/www/class_records -maxdepth 2 -type f | head -20
grep -R "localhost:8000\|/api" -n /var/www/class_records/assets/*.js | head
```

Database checks:

```bash
ls -lh /opt/class_records/data
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

### Backend Could Not Open SQLite Database

Error:

```text
sqlite3.OperationalError: unable to open database file
```

Cause: database path or permissions were wrong.

Fix: use `/opt/class_records/data/prod.db` and make the directory writable:

```bash
mkdir -p /opt/class_records/data
chown -R classrecords:classrecords /opt/class_records/data
```

### Database Or Disk Is Full

Error:

```text
sqlite3.OperationalError: database or disk is full
```

Cause: server disk was full.

Fix: free disk space, then restart:

```bash
systemctl restart class-records
```

### Browser Showed 403 Forbidden

Cause: the uploaded frontend was in the wrong folder shape. `dist` was copied as a whole folder.

Wrong:

```text
/var/www/class_records/dist/index.html
```

Correct:

```text
/var/www/class_records/index.html
```

Fix:

```bash
cp -r /var/www/class_records/dist/* /var/www/class_records/
chmod -R a+rX /var/www/class_records
```

### API Worked Directly But Not Through Nginx Curl Test

This command returned 404:

```bash
curl -i http://127.0.0.1/api/health
```

But this worked in the browser:

```text
http://39.99.137.40/api/health
```

Reason: Nginx chooses the server block by `server_name`. A request to `127.0.0.1` does not match `server_name 39.99.137.40`.

Use this for browser-facing API tests:

```text
http://39.99.137.40/api/health
```

## Future Improvements

Before serious use:

```text
1. Add HTTPS.
2. Add login or private access protection.
3. Add automatic backups for /opt/class_records/data/prod.db.
4. Consider PostgreSQL instead of SQLite for more durable server storage.
5. Consider deploying on a newer OS than CentOS 7 later.
```

Simple SQLite backup command:

```bash
mkdir -p /opt/class_records/backups
cp /opt/class_records/data/prod.db /opt/class_records/backups/prod-$(date +%F-%H%M%S).db
```
