# 📊 Finance Dashboard with Ollama AI
## Portainer-Managed on /mnt/ssd

A **self-hosted, network-only analytics dashboard** for stocks, mutual funds, cryptocurrencies, and ETFs running on your **Raspberry Pi 5** with AI-powered insights using **Ollama**, managed via **Portainer**.

## ✨ Key Features

- **Real-time Financial Data**: Stocks, crypto, ETFs, mutual funds
- **AI-Powered Insights**: Ollama running locally on your Pi
- **Portainer Management**: Web UI for Docker management
- **Completely Private**: Local network + VPN via Wireguard
- **Persistent Storage**: All data on `/mnt/ssd` for easy backups
- **Beautiful Dashboard**: Responsive React frontend
- **Zero Subscription Costs**: Free APIs + your hardware

## 🏗️ Architecture

```
Your Raspberry Pi 5 (1TB SSD at /mnt/ssd)
│
├─ Portainer (Docker Web UI)
│  └─ Manages all services
│
└─ Finance Dashboard Stack
   ├─ FastAPI Backend (Port 8000)
   │  └─ Fetches stock/crypto data
   ├─ Ollama AI Service (Port 11434)
   │  └─ Generates insights
   ├─ React Frontend (Port 3000)
   │  └─ Beautiful dashboard UI
   └─ Nginx Reverse Proxy (Port 80)
      └─ Local network access
```

## 🚀 Quick Start

### 5-Minute Setup

```bash
# 1. SSH into your Pi
ssh pi@192.168.x.x

# 2. Create directory structure
mkdir -p /mnt/ssd/finance-dashboard
mkdir -p /mnt/ssd/ollama/models

# 3. Copy project files to /mnt/ssd/finance-dashboard/

# 4. Deploy via Portainer
# - Open https://your-pi-ip:9443
# - Go to Stacks → Add Stack
# - Upload docker-compose.yml from /mnt/ssd/finance-dashboard/
# - Click Deploy

# 5. Access dashboard
# Open http://your-pi-ip in browser
```

**See [PORTAINER_QUICKSTART.md](PORTAINER_QUICKSTART.md) for detailed steps.**

## 📚 Documentation

### Getting Started
- **[PORTAINER_QUICKSTART.md](PORTAINER_QUICKSTART.md)** ⭐ Start here! 5-minute setup
- **[PORTAINER_GUIDE.md](PORTAINER_GUIDE.md)** - Complete Portainer integration guide
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed configuration & troubleshooting

### Reference
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet
- **[README.md](README.md)** - Original project overview (before Portainer)

### Setup Scripts
- **setup-portainer.sh** - Automated setup for Portainer + /mnt/ssd

## 🎯 Directory Structure on /mnt/ssd

```
/mnt/ssd/
├─ finance-dashboard/           ← All application files
│  ├─ docker-compose.yml       ← Main Portainer config
│  ├─ .env                     ← Environment variables
│  ├─ Dockerfile               ← Container build
│  ├─ requirements.txt          ← Python dependencies
│  ├─ backend/
│  │  └─ main.py              ← FastAPI application
│  ├─ frontend/
│  │  └─ src/                 ← React components
│  ├─ nginx/
│  │  └─ nginx.conf           ← Reverse proxy config
│  ├─ certs/                  ← SSL certificates
│  ├─ cache/                  ← API response cache
│  └─ logs/                   ← Application logs
│
└─ ollama/
   └─ models/                 ← Ollama AI models (persistent)
```

## 🔧 Configuration

### Environment Variables

Edit `/mnt/ssd/finance-dashboard/.env`:

```bash
# Stock data API (optional, free tier sufficient)
ALPHA_VANTAGE_KEY=demo

# Ollama configuration
OLLAMA_HOST=http://ollama:11434

# Python settings
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

### Via Portainer UI

1. Stacks → finance-dashboard → Edit
2. Modify environment variables
3. Re-deploy

## 📊 Using the Dashboard

### Access
- **Local Network**: `http://192.168.x.x`
- **Via Wireguard VPN**: `http://10.x.x.x`
- **Backend API**: `http://your-pi-ip:8000`
- **Portainer**: `https://your-pi-ip:9443`

### Add Assets
1. Type symbol (AAPL, BTC, ETH, etc.)
2. Select asset type (Stock, Crypto, ETF)
3. Click "Add to Portfolio"
4. See real-time price + AI insights

### Monitor in Portainer
- **Containers tab**: See all services running
- **Logs**: Real-time logs from each service
- **Stats**: CPU/Memory usage
- **Exec Console**: Access container shell

## 🔐 Security

✅ **Local Network Only** - No internet exposure by default  
✅ **Wireguard VPN** - Encrypted remote access  
✅ **No Public URLs** - Stay private  
✅ **Self-Hosted** - Complete data control  

Nginx restricts access to:
- `192.168.0.0/16` (local network)
- `10.0.0.0/8` (Wireguard VPN)
- `172.16.0.0/12` (Docker internal)

## 💻 System Requirements

### Your Setup ✅
- **Raspberry Pi 5** (8GB RAM)
- **1TB SSD** at `/mnt/ssd`
- **Portainer** for management

**Perfect for this dashboard!**

## 🚀 Deployment Methods

### Method 1: Portainer UI (Recommended)
- Easiest
- Full web-based management
- Real-time monitoring
- Perfect for non-technical users

**[Follow PORTAINER_QUICKSTART.md](PORTAINER_QUICKSTART.md)**

### Method 2: Command Line
- More control
- Scriptable
- For advanced users

```bash
cd /mnt/ssd/finance-dashboard
docker-compose up -d
```

Portainer automatically detects and lists these containers.

### Method 3: Automated Setup Script
```bash
chmod +x setup-portainer.sh
./setup-portainer.sh
```

Automatically:
- Creates `/mnt/ssd` structure
- Copies files
- Sets permissions
- Starts services
- Generates Portainer guide

## 🎛️ Portainer Features Used

- **Stacks Management** - Deploy/update docker-compose
- **Container Monitoring** - CPU, memory, network stats
- **Real-time Logs** - View container output
- **Exec Console** - Shell access to containers
- **Image Management** - Pull/remove images
- **Volume Management** - Backup/restore data
- **Environment Variables** - Easy config management
- **Labels** - Organized container discovery

## 📈 Performance

On your Raspberry Pi 5:
- **Dashboard load**: ~200ms
- **API response**: 300-800ms
- **Ollama inference**: 2-10 seconds
- **Memory at idle**: ~200-400MB
- **CPU average**: 5-15%
- **Storage (default models)**: ~3-5GB

## 💾 Backup Strategy

### Automated Backups
```bash
# Weekly backup script
tar -czf /mnt/ssd/backups/finance-dashboard-$(date +%Y%m%d).tar.gz \
  /mnt/ssd/finance-dashboard/ \
  /mnt/ssd/ollama/
```

### Via Portainer
- Stacks → finance-dashboard → Inspect
- View volume paths
- Use `tar` or rsync for backup

### Restore
```bash
cd /mnt/ssd
docker-compose down
tar -xzf backups/finance-dashboard-YYYYMMDD.tar.gz
docker-compose up -d
```

## 🔄 Updates & Maintenance

### Update Stack via Portainer
1. Stacks → finance-dashboard → Edit
2. Modify docker-compose.yml
3. Click "Update the stack"

### Update Source Code
```bash
# Edit files on /mnt/ssd
nano /mnt/ssd/finance-dashboard/backend/main.py

# Restart service via Portainer or:
cd /mnt/ssd/finance-dashboard
docker-compose restart backend
```

### Update Ollama Models
```bash
# Via Portainer Exec Console in ollama container:
ollama pull mistral

# Or command line:
docker exec finance-ollama ollama pull mistral
```

## 🆘 Troubleshooting

### Services Won't Start
1. Portainer → Containers → Select service → Logs
2. Check for error messages
3. Verify `/mnt/ssd` permissions and disk space

### High CPU/Memory
1. Portainer → Containers → Stats
2. Check which service is the culprit
3. Restart via Portainer UI

### API Errors
1. Portainer Exec → backend container
2. Run: `curl http://localhost:8000/health`
3. Check logs for detailed errors

**See [PORTAINER_GUIDE.md](PORTAINER_GUIDE.md) for more solutions.**

## 💰 Cost Analysis

| Item | Cost | Notes |
|------|------|-------|
| Raspberry Pi 5 | $80 | One-time |
| 1TB SSD | $100 | One-time |
| Electricity | $0.50/mo | ~5W average |
| APIs | $0 | Free tier sufficient |
| **Total** | **$0.50/mo** | **Operational** |

**Payback period**: 3-4 months vs. paid services

## 🤝 Contributing

Ways to improve:
- Additional data sources (Yahoo Finance, etc.)
- Advanced charting
- Price alerts
- Portfolio backtesting
- Mobile app
- Database persistence

## 📝 License

MIT - See LICENSE file

## 🎓 Learning Resources

- **Portainer Docs**: https://docs.portainer.io/
- **Docker Compose**: https://docs.docker.com/compose/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Ollama**: https://ollama.ai/

## ⚠️ Disclaimer

This is an informational tool only. Not financial advice. Always do your own research before investing.

## 🆘 Getting Help

1. **Quick Issues**: Check [PORTAINER_QUICKSTART.md](PORTAINER_QUICKSTART.md)
2. **Deep Dive**: See [PORTAINER_GUIDE.md](PORTAINER_GUIDE.md)
3. **Commands**: Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. **Full Guide**: Read [SETUP_GUIDE.md](SETUP_GUIDE.md)

## 🎉 Next Steps

1. ✅ Read [PORTAINER_QUICKSTART.md](PORTAINER_QUICKSTART.md)
2. ✅ Copy files to `/mnt/ssd/finance-dashboard/`
3. ✅ Deploy via Portainer UI
4. ✅ Access at `http://your-pi-ip`
5. ✅ Add your favorite assets
6. ✅ Setup Wireguard for VPN access

---

**Your Portainer-managed Finance Dashboard awaits! 🚀**

**Questions?** Start with PORTAINER_QUICKSTART.md →
