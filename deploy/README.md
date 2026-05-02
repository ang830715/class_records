# Server Deployment Notes

This deployment serves the React app with Nginx and runs FastAPI on `127.0.0.1:8000` behind `/api`.

CentOS 7 is past its normal security support window. For an internet-facing app, use firewall rules, HTTPS, and preferably a private access layer such as VPN, Tailscale, or Cloudflare Access.

## 1. Build Locally

From the project root on your computer:

```powershell
cd frontend
$env:VITE_API_BASE="/api"
npm.cmd run build
```

The built frontend files will be in:

```text
frontend/dist
```

## 2. Copy Files To The Server

Push your latest code to GitHub first. Then use your domain or server IP in place of `your-server`.

```powershell
scp -r frontend/dist your-user@your-server:/tmp/class_records_dist
```

## 3. Prepare Server Source Code

On the server:

```bash
sudo useradd --system --home /opt/class_records --shell /sbin/nologin classrecords
sudo mkdir -p /opt/class_records
sudo chown classrecords:classrecords /opt/class_records
sudo -u classrecords git clone https://github.com/YOUR-GITHUB-USER/YOUR-REPO.git /opt/class_records/app
```

If the repository already exists on the server later, update it with:

```bash
cd /opt/class_records/app
sudo -u classrecords git pull --ff-only
```

## 4. Install Frontend Files

On the server:

```bash
sudo mkdir -p /var/www/class_records
sudo cp -r /tmp/class_records_dist/* /var/www/class_records/
sudo chown -R nginx:nginx /var/www/class_records
```

If your Nginx worker does not run as the `nginx` user, replace `nginx:nginx` with the user/group shown by:

```bash
ps -o user,group,args -C nginx
```

## 5. Create Python Environment On CentOS 7

The backend needs Python 3.11+ because it uses `StrEnum`. CentOS 7 usually does not have Python 3.11, so use an isolated Miniforge environment.

```bash
cd /tmp
curl -L -o Miniforge3-Linux-x86_64.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p /opt/class_records/miniforge
/opt/class_records/miniforge/bin/conda create -y -p /opt/class_records/py311 python=3.11 pip
cd /opt/class_records/app/backend
sudo /opt/class_records/py311/bin/python -m pip install --upgrade pip
sudo /opt/class_records/py311/bin/python -m pip install -r requirements.txt
sudo chown -R classrecords:classrecords /opt/class_records/miniforge /opt/class_records/py311
```

Check it:

```bash
/opt/class_records/py311/bin/python --version
```

## 6. Configure Backend Environment

For the first private deployment, SQLite is acceptable:

```bash
sudo cp /opt/class_records/app/deploy/class-records.env.example /etc/class-records.env
sudo vi /etc/class-records.env
```

Set your real domain:

```text
DATABASE_URL=sqlite:////opt/class_records/app/backend/prod.db
ROOT_PATH=/api
CORS_ORIGINS=https://your-domain.example
```

For a more durable setup, replace `DATABASE_URL` with PostgreSQL later.

## 7. Install And Start The Backend Service

```bash
sudo cp /opt/class_records/app/deploy/systemd/class-records.service /etc/systemd/system/class-records.service
sudo systemctl daemon-reload
sudo systemctl enable --now class-records
sudo systemctl status class-records
```

Check the API locally on the server:

```bash
curl http://127.0.0.1:8000/health
```

## 8. Configure Nginx

```bash
sudo cp /opt/class_records/app/deploy/nginx/class-records.conf /etc/nginx/conf.d/class-records.conf
sudo vi /etc/nginx/conf.d/class-records.conf
```

Replace `your-domain.example` with your real domain.

Then:

```bash
sudo nginx -t
sudo setsebool -P httpd_can_network_connect 1
sudo systemctl reload nginx
```

Open:

```text
http://your-domain.example
```

If the server firewall is enabled, allow HTTP traffic:

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

## 9. Useful Server Commands

```bash
sudo systemctl restart class-records
sudo journalctl -u class-records -n 100 --no-pager
sudo nginx -t
sudo systemctl reload nginx
```

## CentOS 7 Nginx Path Note

Some CentOS 7 servers use stock Nginx paths:

```text
/etc/nginx/nginx.conf
/etc/nginx/conf.d/*.conf
```

Your server may use a custom Nginx install instead:

```text
/www/server/nginx/conf/nginx.conf
```

Find the active include directory with:

```bash
sudo /www/server/nginx/sbin/nginx -T | grep -n "include"
```

Copy `deploy/nginx/class-records.conf` into the included virtual-host directory shown by that command, then test and reload with the same Nginx binary:

```bash
sudo /www/server/nginx/sbin/nginx -t -c /www/server/nginx/conf/nginx.conf
sudo systemctl reload nginx
```
