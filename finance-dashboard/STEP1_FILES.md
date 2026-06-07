# 📦 STEP 1 - File Download Guide

## Download ALL these files from the output folder

### 📋 Docker & Config (Root Level)
```
✅ docker-compose-portainer-CORRECTED.yml
✅ Dockerfile
✅ requirements.txt
✅ nginx.conf
✅ .env.example (save as .env)
✅ package.json
```

### 🔧 Backend Files
```
✅ backend_main.py
```

### 🎨 Frontend Files
```
✅ frontend_Dashboard.jsx
✅ frontend_Dashboard.css
✅ src_App.js
✅ src_index.js
✅ public_index.html
```

---

## 📂 How to Organize on Your Pi

After downloading, organize them like this on your Pi:

```bash
cd /mnt/ssd/finance-dashboard/

# 1. Copy root level files
cp docker-compose-portainer-CORRECTED.yml docker-compose.yml
cp Dockerfile .
cp requirements.txt .
cp .env.example .env
cp package.json .

# 2. Create and copy backend
mkdir -p backend
cp backend_main.py backend/main.py

# 3. Create and copy frontend
mkdir -p frontend/public/
mkdir -p frontend/src/

cp public_index.html frontend/public/index.html
cp src_App.js frontend/src/App.js
cp src_index.js frontend/src/index.js
cp frontend_Dashboard.jsx frontend/src/Dashboard.jsx
cp frontend_Dashboard.css frontend/src/Dashboard.css
cp package.json frontend/

# 4. Create and copy nginx
mkdir -p nginx
cp nginx.conf nginx/

# 5. Create empty directories for runtime
mkdir -p certs
mkdir -p cache
mkdir -p logs
```

---

## ✅ Verify Your Structure

After organizing, your `/mnt/ssd/finance-dashboard/` should look like:

```
finance-dashboard/
├─ docker-compose.yml              ✅
├─ Dockerfile                       ✅
├─ requirements.txt                 ✅
├─ .env                            ✅
├─ package.json                    ✅
│
├─ backend/
│  └─ main.py                      ✅
│
├─ frontend/
│  ├─ public/
│  │  └─ index.html                ✅
│  ├─ src/
│  │  ├─ App.js                    ✅
│  │  ├─ index.js                  ✅
│  │  ├─ Dashboard.jsx             ✅
│  │  └─ Dashboard.css             ✅
│  └─ package.json                 ✅
│
├─ nginx/
│  └─ nginx.conf                   ✅
│
├─ certs/                          (empty)
├─ cache/                          (empty)
└─ logs/                           (empty)
```

---

## 🎯 When Ready for Step 1

Run this to verify:

```bash
cd /mnt/ssd/finance-dashboard
ls -la
docker-compose config  # Should show no errors
```

Then tell me:
- ✅ All files organized correctly?
- ✅ `docker-compose config` passes?
- ✅ Ready for Step 2?
