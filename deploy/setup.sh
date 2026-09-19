#!/usr/bin/env bash
# deploy/setup.sh
# One-time server setup script for Ubuntu 22.04 LTS
# Run as root or with sudo

set -e

echo "=== SP-Tech Software Solution Deployment Setup ==="

# 1. System packages
apt-get update -y
apt-get install -y python3-pip python3-venv nginx certbot python3-certbot-nginx \
    libpq-dev build-essential git

# 2. Create app user & directories
id -u sanjivani &>/dev/null || useradd --system --home /var/www/sanjivani --shell /bin/bash sanjivani
mkdir -p /var/www/sanjivani /var/log/sanjivani
chown -R sanjivani:sanjivani /var/www/sanjivani /var/log/sanjivani

# 3. Clone / pull code (adjust URL)
# su sanjivani -c "git clone https://github.com/your-org/sanjivani-one.git /var/www/sanjivani/app"

# 4. Python virtualenv & dependencies
su sanjivani -c "
  python3 -m venv /var/www/sanjivani/venv
  /var/www/sanjivani/venv/bin/pip install -U pip
  /var/www/sanjivani/venv/bin/pip install -r /var/www/sanjivani/app/requirements.txt
"

# 5. Django setup
su sanjivani -c "
  cd /var/www/sanjivani/app
  source /var/www/sanjivani/venv/bin/activate
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  python manage.py populate_sample_data
"

# 6. Systemd service
cat > /etc/systemd/system/sanjivani.service << 'EOF'
[Unit]
Description=SP-Tech Software Solution Gunicorn Daemon
After=network.target

[Service]
User=sanjivani
Group=sanjivani
WorkingDirectory=/var/www/sanjivani/app
ExecStart=/var/www/sanjivani/venv/bin/gunicorn \
    -c /var/www/sanjivani/app/deploy/gunicorn.conf.py \
    sanjivani.wsgi:application
Restart=always
RestartSec=5
EnvironmentFile=/var/www/sanjivani/app/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sanjivani
systemctl start sanjivani

# 7. Nginx
cp /var/www/sanjivani/app/deploy/nginx.conf /etc/nginx/sites-available/sanjivani
ln -sf /etc/nginx/sites-available/sanjivani /etc/nginx/sites-enabled/sanjivani
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. SSL
certbot --nginx -d sanjivani.com -d www.sanjivani.com --non-interactive --agree-tos -m admin@sanjivani.com

echo "=== Setup Complete ==="
