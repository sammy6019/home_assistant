# 🚀 Quick Start: Portainer + /mnt/ssd Setup

Get your Finance Dashboard running on Portainer in **5 minutes**.

---

## ✅ Prerequisites

- Portainer running on your Pi (access at `https://your-pi-ip:9443`)
- `/mnt/ssd` mounted and accessible
- All project files downloaded

---

## 📋 Step-by-Step

### Step 1: Prepare Files (2 minutes)

```bash
# SSH into your Pi
ssh pi@192.168.x.x

# Create directory structure
mkdir -p /mnt/ssd/finance-dashboard
mkdir -p /mnt/ssd/finance-dashboard/{backend,frontend,nginx,certs,cache}
mkdir -p /mnt/ssd/ollama/models

# Copy project files
# (Copy all files from your download into /mnt/ssd/finance-dashboard/)

# Verify structure
ls -la /mnt/ssd/finance-dashboard/
# Should show: Dockerfile, docker-compose.yml, backend/, frontend/, nginx/, etc.
```

### Step 2: Fix Permissions (30 seconds)

```bash
# Make sure everything is accessible
sudo chown -R $USER:$USER /mnt/ssd
chmod -R 755 /mnt/ssd/finance-dashboard
```

### Step 3: Update docker-compose.yml (1 minute)

Use the **Portainer-optimized** version:

**If you downloaded `docker-compose-portainer.yml`:**
```bash
mv /mnt/ssd/finance-dashboard/docker-compose-portainer.yml \
   /mnt/ssd/finance-dashboard/docker-compose.yml
```

**Key differences from original:**
- ✅ Volumes point to `/mnt/ssd/` paths
- ✅ Includes Portainer labels for better UI integration
- ✅ Network configuration optimized for internal communication
- ✅ Resource limits defined for Pi

### Step 4: Create Stack in Portainer (1.5 minutes)

1. **Open Portainer**
   ```
   https://your-pi-ip:9443
   ```

2. **Left sidebar** → **Stacks**

3. **Add Stack** button

4. **Stack name**: `finance-dashboard`

5. **Build method**: Choose one:
   - **Upload**: Browse to `/mnt/ssd/finance-dashboard/docker-compose.yml`
   - **Paste**: Copy-paste contents of docker-compose.yml

6. **Scroll down** → Add environment variables:
   ```
   ALPHA_VANTAGE_KEY=demo
   OLLAMA_HOST=http://ollama:11434
   PYTHONUNBUFFERED=1
   ```

7. **Deploy the stack**

### Step 5: Verify (30 seconds)

After deploy completes:

1. **Containers** tab in Portainer
2. Should see 4 running containers:
   - ✅ `finance-dashboard-api`
   - ✅ `finance-ollama`
   - ✅ `finance-dashboard-frontend`
   - ✅ `finance-dashboard-nginx`

3. Open browser to:
   ```
   http://your-pi-ip
   ```

🎉 **Done!** Your dashboard is running!

---

## 📊 Using Your Dashboard

### Add Assets
1. Type symbol (e.g., `AAPL`, `BTC`, `ETH`)
2. Select type (Stock, Crypto, ETF)
3. Click "Add to Portfolio"

### Monitor via Portainer
1. **Containers** tab
2. Click each container to see:
   - Real-time logs
   - CPU/Memory usage
   - Environment variables

### View Service Logs
- **Containers** → `finance-dashboard-api` → **Logs**
- Real-time updates of what's happening

---

## 🔧 Common Tasks

### Update Configuration

Edit environment variables:
```bash
# Edit on SSD
nano /mnt/ssd/finance-dashboard/.env

# Restart services
cd /mnt/ssd/finance-dashboard
docker-compose restart
```

### Check Service Status

From Pi command line:
```bash
cd /mnt/ssd/finance-dashboard
docker-compose ps

# Or via Portainer: Containers tab
```

### View Real-Time Logs

**Option 1: Portainer**
- Containers → Select service → Logs tab

**Option 2: Command Line**
```bash
cd /mnt/ssd/finance-dashboard
docker-compose logs -f backend
```

### Restart All Services

**Option 1: Portainer**
- Stacks → finance-dashboard → Select containers → Restart

**Option 2: Command Line**
```bash
cd /mnt/ssd/finance-dashboard
docker-compose restart
```

### Change Ollama Model

```bash
# See available models
docker exec finance-ollama ollama list

# Pull a new model
docker exec finance-ollama ollama pull mistral

# Edit backend/main.py line ~180
nano /mnt/ssd/finance-dashboard/backend/main.py
# Change: "model": "neural-chat"
# To:     "model": "mistral"

# Restart backend
cd /mnt/ssd/finance-dashboard
docker-compose restart backend
```

---

## 🔐 VPN Access via Wireguard

Your dashboard is accessible locally. For remote access via VPN:

1. **Access via Wireguard IP**
   ```
   http://10.x.x.x  (your Wireguard IP)
   ```

2. **Dashboard automatically works** - no extra config needed!

3. Nginx restricts access to local network ranges:
   - `192.168.0.0/16`
   - `10.0.0.0/8`
   - `172.16.0.0/12`

---

## 📁 File Structure on /mnt/ssd

```
/mnt/ssd/
├─ finance-dashboard/
│  ├─ docker-compose.yml      ← Main config
│  ├─ .env                     ← Environment vars
│  ├─ Dockerfile              ← Build instructions
│  ├─ requirements.txt         ← Python deps
│  ├─ backend/
│  │  └─ main.py              ← FastAPI app
│  ├─ frontend/
│  │  ├─ public/
│  │  ├─ src/
│  │  └─ Dockerfile
│  ├─ nginx/
│  │  ├─ nginx.conf           ← Reverse proxy
│  │  └─ logs/                ← Access logs
│  ├─ certs/                  ← SSL certificates
│  ├─ cache/                  ← API cache
│  └─ logs/                   ← Application logs
│
└─ ollama/
   └─ models/                 ← AI models (persistent)
```

---

## 🆘 Troubleshooting

### Services won't start?

1. Check Portainer logs:
   - Containers tab → Select container → Logs
   - Look for error messages

2. Common issues:
   ```bash
   # Port already in use?
   sudo lsof -i :8000
   
   # Directory permissions?
   ls -la /mnt/ssd/finance-dashboard/
   
   # Disk space?
   df -h /mnt/ssd
   ```

3. Restart from command line:
   ```bash
   cd /mnt/ssd/finance-dashboard
   docker-compose down
   docker-compose up -d
   ```

### Dashboard not loading?

1. Check if frontend is running:
   - Portainer: Containers → `finance-dashboard-frontend` should be green

2. Test backend API:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check Nginx logs:
   ```bash
   docker-compose logs nginx
   ```

### Ollama slow?

- First inference takes 1-2 minutes (normal!)
- Check logs: `docker-compose logs ollama`
- Check memory: `free -h`

---

## 📚 More Documentation

- **Full Setup**: See `SETUP_GUIDE.md`
- **Portainer Deep Dive**: See `PORTAINER_GUIDE.md`
- **Command Reference**: See `QUICK_REFERENCE.md`

---

## 🎯 Next Steps

1. ✅ Add your API key to `.env`
2. ✅ Test with a stock symbol (try AAPL)
3. ✅ Test with crypto (try BTC, ETH)
4. ✅ Setup Wireguard for remote access
5. ✅ Create backup of /mnt/ssd folder

---

**Your Portainer-managed Finance Dashboard is ready! 🚀**
