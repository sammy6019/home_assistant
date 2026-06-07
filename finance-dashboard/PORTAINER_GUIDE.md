# 🎛️ Portainer Integration Guide

## Overview

This guide covers setting up and managing the Finance Dashboard through **Portainer** on your Raspberry Pi 5, with all files stored on `/mnt/ssd`.

**Portainer** provides:
- 🖥️ Web UI for container management
- 📊 Real-time monitoring & stats
- 📋 Stack/compose file management
- 🔍 Container logs & shell access
- 💾 Volume management
- 🔄 Easy updates & rollbacks

---

## Prerequisites

### 1. Portainer Installation

If you don't have Portainer installed, set it up first:

```bash
# Create volume for Portainer data
docker volume create portainer_data

# Run Portainer
docker run -d \
  -p 8000:8000 \
  -p 9443:9443 \
  --name=portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

Access Portainer at: `https://your-pi-ip:9443`

### 2. /mnt/ssd Preparation

Ensure your SSD is mounted and ready:

```bash
# Check if mounted
df /mnt/ssd

# If not mounted, mount it:
sudo mkdir -p /mnt/ssd
sudo mount /dev/sdX1 /mnt/ssd  # Replace sdX1 with your device

# Make it readable/writable
sudo chown $USER:$USER /mnt/ssd
chmod 755 /mnt/ssd
```

---

## Deployment Method 1: Using Portainer UI

### Step 1: Prepare Files

```bash
# On your Pi:
cd /mnt/ssd
mkdir -p finance-dashboard

# Copy all project files to /mnt/ssd/finance-dashboard/
# (docker-compose.yml, Dockerfile, backend/, frontend/, nginx/, etc.)
```

### Step 2: Create Stack in Portainer

1. **Open Portainer**
   - Navigate to `https://your-pi-ip:9443`
   - Login with your credentials

2. **Go to Stacks**
   - Left menu → **Stacks**
   - Click **Add Stack**

3. **Configure Stack**
   - **Name**: `finance-dashboard`
   - **Build method**: 
     - Option A: **Upload** → Select `docker-compose.yml` from `/mnt/ssd/finance-dashboard/`
     - Option B: **Editor** → Paste contents of docker-compose.yml

4. **Set Environment Variables**
   - Scroll to **Environment variables**
   - Add your settings:
     ```
     ALPHA_VANTAGE_KEY = your-api-key-here
     OLLAMA_HOST = http://ollama:11434
     PYTHONUNBUFFERED = 1
     ```

5. **Deploy**
   - Click **Deploy the stack**
   - Wait for confirmation

### Step 3: Verify Deployment

1. **Check Containers**
   - Go to **Containers**
   - Should see:
     - `finance-dashboard-api`
     - `finance-ollama`
     - `finance-dashboard-frontend`
     - `finance-dashboard-nginx`

2. **Verify Health**
   - Each container should show **"Running"** status (green)
   - Click on each container to check **Logs**

3. **Test Access**
   - Open browser: `http://your-pi-ip`
   - Should see Finance Dashboard

---

## Deployment Method 2: CLI with Portainer Awareness

Use this if you prefer command line but want Portainer to manage it:

```bash
# Navigate to project
cd /mnt/ssd/finance-dashboard

# Deploy using docker-compose
docker-compose up -d

# Portainer will automatically detect and list these containers
```

Portainer will automatically discover and list all running containers in the UI.

---

## Managing Stack via Portainer

### View Stack Status

1. **Stacks** → Select `finance-dashboard`
2. See all services and their status
3. View resource usage per container

### Update Stack

#### Method 1: Re-deploy from File
1. **Stacks** → `finance-dashboard`
2. Click **Edit**
3. Update docker-compose.yml in the editor
4. Click **Update the stack**

#### Method 2: Update from SSD File
1. Edit `/mnt/ssd/finance-dashboard/docker-compose.yml` locally
2. In Portainer: **Stacks** → `finance-dashboard` → **Edit**
3. Copy updated contents
4. Click **Update the stack**

### Monitor Containers

```
Containers Tab:
├─ finance-dashboard-api
│  ├─ Status: Running (green)
│  ├─ CPU/Memory: Real-time stats
│  ├─ Logs: Click to view
│  └─ Exec: Interactive shell
├─ finance-ollama
│  ├─ Status: Running
│  ├─ Stats: Shows AI model load
│  └─ Logs: Model downloads/inference
├─ finance-dashboard-frontend
│  ├─ Status: Running
│  └─ Logs: React build/server logs
└─ finance-dashboard-nginx
   ├─ Status: Running
   └─ Logs: Reverse proxy access logs
```

### Access Container Shell

For debugging or management:

1. **Containers** → Select container (e.g., `finance-dashboard-api`)
2. Click **Exec Console**
3. Run commands:

```bash
# In backend container:
curl http://localhost:8000/health

# In Ollama container:
ollama list
ollama pull mistral

# In nginx container:
nginx -t  # Test config
```

### View Logs with Filters

1. **Containers** → Select container
2. **Logs** tab
3. Filter options:
   - Search by keyword
   - Follow in real-time
   - Timestamp filtering
   - Last N lines

---

## Volume Management via Portainer

### Understanding Volumes

Your Finance Dashboard stores data at:

```
/mnt/ssd/
├─ finance-dashboard/
│  ├─ backend/           (source code)
│  ├─ frontend/          (React app)
│  ├─ nginx/             (config & logs)
│  ├─ certs/             (SSL certificates)
│  ├─ cache/             (API cache)
│  ├─ docker-compose.yml
│  └─ .env
└─ ollama/
   └─ models/            (AI models)
```

### Manage Volumes in Portainer

1. **Volumes** tab
2. View all volumes used by containers
3. Inspect volume details:
   - Mountpoint
   - Driver
   - Labels

### Backup Volumes

```bash
# Backup via command line
cd /mnt/ssd
tar -czf finance-dashboard-backup-$(date +%Y%m%d).tar.gz \
  finance-dashboard/ ollama/

# Then download from your backup location
```

---

## Monitoring & Alerts

### Dashboard Metrics

In Portainer main dashboard:
- CPU usage per container
- Memory usage trends
- Running container count
- Image count

### Per-Container Stats

1. **Containers** → Select container
2. **Stats** tab shows:
   - Real-time CPU %
   - Memory usage MB
   - Network I/O
   - Block I/O

### Setting Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 512M
        reservations:
          cpus: '1'
          memory: 256M
```

Then redeploy through Portainer.

---

## Network Management

### Accessing Services

**Local Network:**
```
Frontend: http://192.168.x.x
Backend:  http://192.168.x.x:8000
```

**Via Wireguard VPN:**
```
Frontend: http://10.x.x.x
Backend:  http://10.x.x.x:8000
```

### Container Networks

In Portainer:
1. **Networks** tab
2. View `finance-network` (used for inter-service communication)
3. Services can communicate internally via container name:
   - `backend:8000`
   - `ollama:11434`

---

## Updating & Rollback

### Check for Updates

1. **Images** tab
2. See if newer versions available
3. Pull new versions if desired

### Rolling Back

Portainer doesn't store old compose files by default, so:

1. **Keep backups** of docker-compose.yml
   ```bash
   cp /mnt/ssd/finance-dashboard/docker-compose.yml \
      /mnt/ssd/finance-dashboard/docker-compose.yml.backup
   ```

2. **If issues occur**, restore and redeploy:
   ```bash
   cd /mnt/ssd/finance-dashboard
   cp docker-compose.yml.backup docker-compose.yml
   docker-compose down
   docker-compose up -d
   ```

---

## Troubleshooting via Portainer

### Service Won't Start

1. **Containers** → Click problem container
2. **Logs** tab → Check error messages
3. Common issues:
   - Port already in use
   - Volume mount path doesn't exist
   - Missing environment variables

**Fix example:**
```bash
# Port in use? Check what's using it:
sudo lsof -i :8000

# Path doesn't exist? Create it:
sudo mkdir -p /mnt/ssd/finance-dashboard/cache
```

### High CPU Usage

1. **Dashboard** → See which container uses CPU
2. Click container → **Stats**
3. Check if:
   - Ollama is running inference (normal - temp usage)
   - Backend stuck in loop (restart)
   - Nginx high (unlikely unless heavy traffic)

**Actions:**
```bash
# Check what Ollama is doing
docker exec finance-ollama top

# Restart if stuck
docker-compose restart backend
```

### Out of Disk Space

1. **Check available space**:
   ```bash
   df -h /mnt/ssd
   ```

2. **Clean up Docker**:
   ```bash
   # Remove unused images
   docker image prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

3. **Check what's using space**:
   ```bash
   du -sh /mnt/ssd/ollama/models/  # Ollama models
   du -sh /mnt/ssd/finance-dashboard/  # Project files
   ```

### API Endpoints Down

1. **Test from Portainer console**:
   ```bash
   # Exec into backend container
   curl http://localhost:8000/health
   ```

2. **Check logs**:
   - **Containers** → `finance-dashboard-api` → **Logs**
   - Look for error messages

3. **Restart**:
   ```bash
   docker-compose restart backend
   ```

---

## Advanced Portainer Features

### Environment Variable Management

Store sensitive values in Portainer:

1. **Stack** → **Environment variables**
2. Set `ALPHA_VANTAGE_KEY` and other secrets
3. These override values in `.env` file

### Webhooks (Auto-Deploy on Git)

Set up webhooks to auto-deploy on code changes:
1. **Webhooks** tab
2. Enable webhook for stack
3. Use webhook URL in GitHub/GitLab

### Custom Templates

Create reusable stack templates:
1. **App Templates** → **Custom Templates**
2. Add your docker-compose.yml as template
3. Quick-deploy new instances

---

## Backup & Disaster Recovery

### Full Backup Strategy

```bash
# Weekly backup script
#!/bin/bash
BACKUP_DIR="/mnt/ssd/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup all data
tar -czf $BACKUP_DIR/finance-dashboard-$DATE.tar.gz \
  /mnt/ssd/finance-dashboard/ \
  /mnt/ssd/ollama/ \
  --exclude='/mnt/ssd/*/node_modules' \
  --exclude='/mnt/ssd/*/__pycache__'

echo "Backup created: $BACKUP_DIR/finance-dashboard-$DATE.tar.gz"

# Keep only last 4 backups
find $BACKUP_DIR -name "finance-dashboard-*.tar.gz" \
  -type f -mtime +30 -delete
```

### Restore from Backup

```bash
# Stop services
cd /mnt/ssd/finance-dashboard
docker-compose down

# Restore backup
cd /mnt/ssd
tar -xzf backups/finance-dashboard-YYYYMMDD_HHMMSS.tar.gz

# Restart services
cd finance-dashboard
docker-compose up -d
```

---

## Best Practices

✅ **DO:**
- Use Portainer for monitoring (it's excellent for that)
- Keep docker-compose.yml backed up
- Review logs regularly
- Set resource limits to prevent runaway processes
- Monitor disk space on /mnt/ssd
- Use .env for sensitive data

❌ **DON'T:**
- Manually edit containers in Portainer then expect docker-compose to work
- Delete volumes without backup
- Leave default Portainer passwords
- Ignore high CPU/memory warnings
- Store API keys in version control

---

## Quick Command Reference

```bash
# From /mnt/ssd/finance-dashboard/:

# View all logs
docker-compose logs -f

# View specific container logs
docker-compose logs -f backend

# Check status
docker-compose ps

# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart ollama

# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Rebuild images
docker-compose build --no-cache

# Remove old images
docker image prune -a

# Check container resource usage
docker stats

# Update .env and reload
docker-compose restart
```

---

## Getting Help

### From Portainer
- Check **Container Logs** for specific errors
- Use **Exec Console** to run diagnostic commands
- Monitor **Stats** to identify resource issues

### From Command Line
```bash
cd /mnt/ssd/finance-dashboard
docker-compose logs -f  # See all logs
docker-compose ps       # See status
```

### Community Resources
- Portainer Docs: https://docs.portainer.io/
- Docker Compose Docs: https://docs.docker.com/compose/
- Check dashboard logs for detailed error messages

---

**Your Finance Dashboard is now Portainer-managed on /mnt/ssd! 🎯**
