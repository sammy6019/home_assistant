# 📸 Portainer Deployment Visual Guide

Step-by-step screenshots and descriptions for deploying Finance Dashboard via Portainer.

---

## 🔗 Access Portainer

### Step 1: Open Portainer
```
URL: https://your-pi-ip:9433

Example: https://192.168.1.100:9433
```

**What you'll see:**
- Portainer login screen (dark/light theme)
- Login with your Portainer credentials

---

## 📋 Navigate to Stacks

### Step 2: Go to Stacks Menu

**Click on the left sidebar:**
```
Sidebar → Stacks
```

**Location:** Should show "Stacks" with a stack icon

**What you'll see:**
- List of existing stacks (if any)
- "Add Stack" button in top right
- Empty list if first deployment

---

## ➕ Create New Stack

### Step 3: Click "Add Stack"

**Button location:** Top right of Stacks page

**What you'll see after clicking:**
- Stack creation form
- Three tabs:
  1. **Build method** (Upload, Editor, Repository)
  2. **Stack details**
  3. **Environment variables**

---

## 📝 Fill Stack Details

### Step 4: Configure Stack

**Field 1: Name**
```
Input: finance-dashboard
```

**Field 2: Build method**
Choose one:

#### Option A: Upload from File
```
Select: Upload
Click: "Select file"
Navigate to: /mnt/ssd/finance-dashboard/docker-compose.yml
Click: Upload
```

#### Option B: Paste Contents
```
Select: Editor
Paste contents of docker-compose.yml into text area
```

#### Option C: From Repository
```
Select: Repository
URL: (only if using Git)
```

**Recommendation:** Use **Upload** or **Editor** for local deployment

---

## 🔑 Set Environment Variables

### Step 5: Configure Environment

**Scroll down to "Environment variables" section**

**Add each variable:**

```
Variable 1:
Name:  ALPHA_VANTAGE_KEY
Value: demo
(Or your actual API key)

Variable 2:
Name:  OLLAMA_HOST
Value: http://ollama:11434

Variable 3:
Name:  PYTHONUNBUFFERED
Value: 1
```

**Click "+ Add variable" for each one**

---

## 🚀 Deploy Stack

### Step 6: Deploy

**Scroll to bottom**

**Click: "Deploy the stack"**

**What happens:**
- Portainer validates docker-compose.yml
- Shows deployment progress
- Creates containers
- Starts services
- Takes 15-30 seconds

**What you'll see:**
- Success message
- Stack now appears in Stacks list
- Spinner while pulling images

---

## ✅ Verify Deployment

### Step 7: Check Containers

**Navigate to:** Containers (left sidebar)

**What you should see:**
```
Container Name                    Status    Image
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
finance-dashboard-api             Running   (custom)
finance-ollama                    Running   ollama/ollama
finance-dashboard-frontend        Running   (custom)
finance-dashboard-nginx           Running   nginx:alpine
```

**All should be GREEN "Running"**

If any are **red/exited**:
- Click the container
- Check **Logs** tab
- Look for error messages

---

## 🔍 Viewing Container Details

### Step 8: Inspect Containers

**Click any container** (e.g., `finance-dashboard-api`)

**You'll see tabs:**

**1. Overview Tab**
```
Container ID, Status, Image, Port mappings
```

**2. Logs Tab** ⭐ Most useful
```
Real-time output
Refresh automatically
Can search/filter
```

**3. Inspect Tab**
```
Full container configuration
Environment variables
Volume mounts
```

**4. Stats Tab** (if supported)
```
CPU usage: ___%
Memory: __ MB
Network I/O
```

**5. Exec Console Tab**
```
Terminal access to container
Run commands like:
  - curl http://localhost:8000/health
  - ollama list
  - ps aux
```

---

## 🔄 Updating Stack

### When You Need to Update

**Scenario 1: Change environment variables**
```
Stacks → finance-dashboard → Edit
Modify "Environment variables" section
Click "Update the stack"
```

**Scenario 2: Update docker-compose.yml**
```
Stacks → finance-dashboard → Edit
Paste new docker-compose.yml contents
Click "Update the stack"
```

**Scenario 3: Restart services**
```
Containers → Select containers you want to restart
Click "Restart" button
```

---

## 📊 Monitoring Dashboard

### Main Dashboard Features

**Top of Portainer dashboard shows:**

```
┌─────────────────────────────────────────┐
│ Environment Status                      │
├─────────────────────────────────────────┤
│ Running: 4 containers                  │
│ Paused:  0 containers                  │
│ Stopped: 0 containers                  │
│ Unhealthy: 0 containers                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ System Stats                            │
├─────────────────────────────────────────┤
│ CPU: 12.4%                              │
│ Memory: 456 MB / 7.7 GB                │
│ Network: ↑ 2.1 MB/s ↓ 3.2 MB/s        │
└─────────────────────────────────────────┘
```

---

## 🔐 Security & Access Control

### Configure Access Permissions

**Edit Stack → Access Control**

```
Public: Anyone can access (default)
Restricted: Only specific users
Private: Only admin
```

**Recommendation:**
- Keep as **Public** for local network
- Or **Restricted** to specific users
- Wireguard provides network-level protection

---

## 🔄 Common Operations

### Restart All Services
```
Stacks → finance-dashboard
Select all containers
Click "Restart"
```

### View Real-Time Logs
```
Containers → Select service
"Logs" tab
See output in real-time
```

### Access Container Shell
```
Containers → Select service
"Exec Console" tab
Type commands:
  curl http://localhost:8000/health
  ollama list
  ls -la /tmp/
```

### Update Configuration
```
Edit .env file on /mnt/ssd/
Restart containers via Portainer
```

### Clean Up Images
```
Images → Select unused images
Delete
Frees up disk space
```

---

## 📈 Performance Monitoring

### Check Resource Usage

**Real-time monitoring:**

```
Portainer Dashboard → See live CPU/Memory

Or per-container:
Containers → Select container → Stats

Shows:
- CPU percentage
- Memory usage (MB)
- Network I/O (bytes)
- Block I/O
```

### Check Disk Usage

```
Containers → Select container
Inspect tab → Mounts section
Shows volume paths and sizes
```

### Monitor from CLI

```bash
# From your Pi command line:
docker stats

# Specific container:
docker stats finance-dashboard-api
```

---

## 🆘 Troubleshooting in Portainer

### Problem: Container won't start

**Steps:**
1. Containers tab → Select problem container
2. Click container → **Logs** tab
3. Read error messages
4. Common causes:
   - Port already in use
   - Volume path doesn't exist
   - Missing environment variable

**Fix:**
```bash
# On Pi:
mkdir -p /mnt/ssd/finance-dashboard/cache
chmod -R 755 /mnt/ssd/finance-dashboard/
```

### Problem: High CPU Usage

**Steps:**
1. Dashboard → See which container uses CPU
2. Click container → **Stats** tab
3. Check if:
   - Ollama running inference (normal, temporary)
   - Backend stuck processing
   - Nginx heavy load

**Action:**
- Restart container via Portainer
- Check logs for infinite loops
- Reduce resource limits if needed

### Problem: Disk Full

**Steps:**
1. Note available space: `df -h /mnt/ssd`
2. Identify large items:
   - Images → cleanup old versions
   - Volumes → check sizes
   - Logs → may be large

**Action:**
```bash
# Clean up
docker image prune -a
docker volume prune

# Or check specific paths:
du -sh /mnt/ssd/ollama/models/
du -sh /mnt/ssd/finance-dashboard/
```

---

## 🔗 Quick Reference

### Portainer URLs

```
Main UI:        https://your-pi-ip:9443
API:            https://your-pi-ip:9443/api
Swagger Docs:   https://your-pi-ip:9443/swagger
```

### Finance Dashboard URLs

```
Local Network:
  Frontend:     http://192.168.x.x
  Backend API:  http://192.168.x.x:8000
  Docs:         http://192.168.x.x:8000/docs

Via Wireguard VPN:
  Frontend:     http://10.x.x.x
  Backend API:  http://10.x.x.x:8000
```

---

## 📋 Deployment Checklist

Use this to verify your deployment:

```
Pre-Deployment:
☐ Portainer is running
☐ /mnt/ssd is mounted and writable
☐ Project files copied to /mnt/ssd/finance-dashboard/

Deployment:
☐ Opened Portainer UI
☐ Navigated to Stacks
☐ Created new stack "finance-dashboard"
☐ Uploaded/pasted docker-compose.yml
☐ Set environment variables
☐ Clicked "Deploy the stack"

Post-Deployment:
☐ All 4 containers running (green status)
☐ Check logs for errors
☐ Test API: http://your-pi-ip:8000/health
☐ Open dashboard: http://your-pi-ip
☐ Add test asset (AAPL or BTC)

Optional:
☐ Setup Wireguard for VPN access
☐ Configure backups
☐ Fine-tune Ollama model
```

---

## 🎓 Learning Tips

1. **Explore the Logs** - Best way to understand what's happening
2. **Use Exec Console** - Directly test services
3. **Monitor Stats** - See resource usage in real-time
4. **Keep docker-compose.yml backed up** - Save versions
5. **Use environment variables** - Don't hardcode secrets

---

**You're now a Portainer expert! 🎉**

For more details, see [PORTAINER_GUIDE.md](PORTAINER_GUIDE.md)
