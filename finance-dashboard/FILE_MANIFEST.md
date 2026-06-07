# 📦 Finance Dashboard - Portainer + /mnt/ssd Edition

## 🎯 What You're Getting

A complete, **Portainer-managed Finance Dashboard** deployed on your Raspberry Pi 5 with all files stored on `/mnt/ssd` for easy management and backups.

---

## 📂 File Manifest

### 📚 Documentation Files (Start Here!)

| File | Purpose | Start With? |
|------|---------|-------------|
| **README_PORTAINER.md** | 👈 **START HERE** - Overview for Portainer setup | ✅ YES |
| **PORTAINER_QUICKSTART.md** | 5-minute deployment guide | ✅ YES |
| **PORTAINER_VISUAL_GUIDE.md** | Step-by-step screenshots/descriptions | 📖 Reference |
| **PORTAINER_GUIDE.md** | Complete Portainer deep dive | 📖 Reference |
| **SETUP_GUIDE.md** | Original detailed setup guide | 📖 Advanced |
| **QUICK_REFERENCE.md** | Command cheat sheet | 🔧 Utility |

### 🐳 Docker Configuration

| File | Purpose |
|------|---------|
| **docker-compose-portainer.yml** | 👈 **USE THIS** - Portainer-optimized compose file |
| **docker-compose.yml** | Original compose (deprecated for Portainer) |
| **Dockerfile** | Container build instructions for backend |
| **.env.example** | Environment variables template |
| **.gitignore** | Git ignore file |

### 🔧 Application Files

| File | Purpose |
|------|---------|
| **backend_main.py** | FastAPI backend with Ollama integration |
| **requirements.txt** | Python dependencies |
| **nginx.conf** | Nginx reverse proxy configuration |
| **frontend_Dashboard.jsx** | React dashboard component |
| **frontend_Dashboard.css** | Dashboard styling |
| **src_App.js** | React app wrapper |
| **src_index.js** | React entry point |
| **public_index.html** | HTML template |
| **package.json** | Frontend dependencies |

### 🚀 Setup Scripts

| File | Purpose |
|------|---------|
| **setup-portainer.sh** | Automated Portainer + /mnt/ssd setup |
| **setup.sh** | Original setup (for non-Portainer) |

---

## ⚙️ Setup Instructions

### For Your Portainer + /mnt/ssd Setup:

#### **Step 1: Use Portainer-Optimized Files**

Copy these specific files to `/mnt/ssd/finance-dashboard/`:

```
Essential:
✅ docker-compose-portainer.yml  → rename to docker-compose.yml
✅ Dockerfile
✅ requirements.txt
✅ .env.example                  → copy to .env

Backend:
✅ backend/
   └─ main.py                    (from backend_main.py)

Frontend:
✅ frontend/
   ├─ public/
   │  └─ index.html              (from public_index.html)
   ├─ src/
   │  ├─ App.js                  (from src_App.js)
   │  ├─ Dashboard.jsx           (from frontend_Dashboard.jsx)
   │  ├─ Dashboard.css           (from frontend_Dashboard.css)
   │  └─ index.js                (from src_index.js)
   └─ package.json

Nginx:
✅ nginx/
   └─ nginx.conf
```

#### **Step 2: Follow Quick Start**

```bash
# Read this first:
PORTAINER_QUICKSTART.md

# Or use automated script:
chmod +x setup-portainer.sh
./setup-portainer.sh
```

#### **Step 3: Deploy via Portainer**

1. Open: `https://your-pi-ip:9443`
2. Stacks → Add Stack
3. Upload: `/mnt/ssd/finance-dashboard/docker-compose.yml`
4. Deploy

---

## 🗂️ Storage Layout on /mnt/ssd

```
/mnt/ssd/
│
├─ finance-dashboard/              ← All application files
│  ├─ docker-compose.yml           ← MAIN config for Portainer
│  ├─ .env                         ← Environment variables
│  ├─ Dockerfile                   ← Build instructions
│  ├─ requirements.txt              ← Python deps
│  │
│  ├─ backend/                     ← FastAPI backend
│  │  └─ main.py
│  │
│  ├─ frontend/                    ← React frontend
│  │  ├─ public/
│  │  │  └─ index.html
│  │  ├─ src/
│  │  │  ├─ App.js
│  │  │  ├─ Dashboard.jsx
│  │  │  ├─ Dashboard.css
│  │  │  └─ index.js
│  │  └─ package.json
│  │
│  ├─ nginx/                       ← Nginx reverse proxy
│  │  ├─ nginx.conf
│  │  └─ logs/                     ← Generated at runtime
│  │
│  ├─ certs/                       ← SSL certificates (optional)
│  ├─ cache/                       ← API cache (generated)
│  ├─ logs/                        ← Application logs (generated)
│  │
│  └─ backups/                     ← Your backup location
│
└─ ollama/
   └─ models/                      ← Persistent AI models
      ├─ neural-chat/
      ├─ mistral/
      └─ ...
```

---

## 🔄 Key Differences from Original Setup

### Original (docker-compose.yml)
```yaml
volumes:
  - finance_cache:/tmp/finance_cache
  - ollama_data:/root/.ollama
```

### Portainer-Optimized (docker-compose-portainer.yml)
```yaml
volumes:
  - /mnt/ssd/finance-dashboard/backend:/app
  - /mnt/ssd/finance-dashboard/cache:/tmp/finance_cache
  - /mnt/ssd/ollama/models:/root/.ollama
```

**Benefits:**
- ✅ Easy file access on `/mnt/ssd`
- ✅ Simple backups (just tar the directory)
- ✅ Portainer UI integration
- ✅ No Docker volume management needed

---

## 📖 Reading Order

### If You're New to Portainer:

1. **README_PORTAINER.md** - Overview (10 min)
2. **PORTAINER_QUICKSTART.md** - Deploy (5 min)
3. **PORTAINER_VISUAL_GUIDE.md** - Visual reference (10 min)
4. **PORTAINER_GUIDE.md** - Deep dive (30 min)

### If You Know Portainer:

1. **PORTAINER_QUICKSTART.md** - Just deploy! (5 min)
2. **docker-compose-portainer.yml** - Check config
3. Reference others as needed

### For Troubleshooting:

1. **PORTAINER_GUIDE.md** - "Troubleshooting via Portainer" section
2. **QUICK_REFERENCE.md** - Command reference
3. **SETUP_GUIDE.md** - Original detailed guide

---

## 🎯 Quick Navigation

### Need to...

**Deploy the dashboard?**
→ **PORTAINER_QUICKSTART.md**

**Manage via Portainer UI?**
→ **PORTAINER_VISUAL_GUIDE.md**

**Configure in detail?**
→ **PORTAINER_GUIDE.md**

**Run commands?**
→ **QUICK_REFERENCE.md**

**Debug issues?**
→ **PORTAINER_GUIDE.md** (Troubleshooting section)

**Original setup (non-Portainer)?**
→ **README.md** + **SETUP_GUIDE.md**

---

## ⚡ The 5-Minute Path

```bash
# 1. Copy files to /mnt/ssd
mkdir -p /mnt/ssd/finance-dashboard
# Copy all project files here

# 2. Read quick start
cat PORTAINER_QUICKSTART.md

# 3. Open Portainer
# https://your-pi-ip:9433

# 4. Deploy (upload docker-compose-portainer.yml)
# Stacks → Add Stack → Upload docker-compose.yml

# 5. Access dashboard
# http://your-pi-ip

# DONE! 🎉
```

---

## 🔐 Security Notes

### What's Changed
- Volumes now on `/mnt/ssd` (file system level)
- Portainer labels added for UI organization
- Network defined for inter-service communication
- Same Nginx security restrictions (local network + Wireguard)

### What's Secure
- ✅ Still local network only
- ✅ VPN access via Wireguard
- ✅ API keys in .env (not in code)
- ✅ No public internet exposure

---

## 💾 Backup & Restore

### With /mnt/ssd Setup

**Backup is simple:**
```bash
tar -czf finance-dashboard-backup.tar.gz /mnt/ssd/
```

**Restore is simple:**
```bash
tar -xzf finance-dashboard-backup.tar.gz
# Everything is back, including Ollama models
```

**Via Portainer:**
1. Services are persistent on disk
2. Just backup `/mnt/ssd` folder
3. Copy to external drive for safety

---

## 🆘 Common Questions

### Q: Which docker-compose file should I use?
**A:** Use `docker-compose-portainer.yml` (specifically optimized for Portainer + /mnt/ssd)

### Q: Where do I copy the files?
**A:** `/mnt/ssd/finance-dashboard/` - it's all configured for this path

### Q: Do I need to use Portainer?
**A:** No - you can still use `docker-compose up -d` from `/mnt/ssd/finance-dashboard/`. Portainer just provides a nice UI.

### Q: Can I access files while containers are running?
**A:** Yes! Files on `/mnt/ssd` are accessible anytime. Portainer/Docker don't lock them.

### Q: How do I backup?
**A:** Just backup `/mnt/ssd` folder. Everything persists there - no Docker volumes to manage.

### Q: Can I move /mnt/ssd to another drive?
**A:** Yes - just update paths in docker-compose.yml and restart.

---

## 📊 File Purposes at a Glance

```
docker-compose-portainer.yml
    ↓
    Defines: 4 services (backend, ollama, frontend, nginx)
    Volumes: Point to /mnt/ssd paths
    Networks: Internal communication
    Labels: Portainer UI organization

Dockerfile
    ↓
    Builds: FastAPI backend image (ARM64 optimized)

backend/main.py
    ↓
    Runs: FastAPI server
    Connects: Stock API, Crypto API, Ollama
    Serves: REST API endpoints

frontend/src/
    ↓
    Runs: React web app
    Displays: Beautiful dashboard UI
    Calls: Backend API

nginx/nginx.conf
    ↓
    Routes: Requests to backend/frontend
    Restricts: To local network + Wireguard IPs

ollama/models/
    ↓
    Stores: AI models (persistent, large)
    Used: For insights generation
```

---

## 🚀 You're Ready!

### Next Steps:

1. **Read** PORTAINER_QUICKSTART.md (5 min)
2. **Copy** project files to `/mnt/ssd/finance-dashboard/`
3. **Rename** docker-compose-portainer.yml to docker-compose.yml
4. **Deploy** via Portainer UI
5. **Access** at `http://your-pi-ip`

---

## 📞 Support

- **Quick deploy?** → PORTAINER_QUICKSTART.md
- **Visual guide?** → PORTAINER_VISUAL_GUIDE.md
- **Advanced?** → PORTAINER_GUIDE.md
- **Commands?** → QUICK_REFERENCE.md
- **Issues?** → Check docs/TROUBLESHOOTING.md section in PORTAINER_GUIDE.md

---

**Your Portainer-managed Finance Dashboard is ready to deploy! 🎉**

Start with: **README_PORTAINER.md** →
