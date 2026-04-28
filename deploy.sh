#!/bin/bash

echo "🚀 Starting deployment..."

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv git nginx curl

# Create app directory
mkdir -p /opt/elderly-care
cd /opt/elderly-care

# (你需要改这里)
# clone你的项目
git clone https://your-repo-url.git .

# Create virtual env
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f .env ]; then
  echo "Creating .env..."
  echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
fi

# Create systemd service
cat <<EOF > /etc/systemd/system/elderly-care.service
[Unit]
Description=Elderly Care App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/elderly-care
ExecStart=/opt/elderly-care/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable elderly-care
systemctl start elderly-care

# Configure Nginx
cat <<EOF > /etc/nginx/sites-available/default
server {
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

systemctl restart nginx

# Test
curl http://localhost:8000/health

echo "✅ Deployment finished!"
