# Finance Dashboard Setup Guide

A complete local analytics dashboard for stocks, crypto, ETFs, and mutual funds with AI-powered insights via Ollama.

## Prerequisites

- **Raspberry Pi 5** with 1TB SSD (or similar ARM64 device)
- **Docker & Docker Compose** installed
- **VPN** access configured (Wireguard recommended)
- Internet connection for fetching financial data
- Basic knowledge of command line

## Quick Start (10 minutes)

### 1. Install Docker on Raspberry Pi

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (optional, avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt-get install -y docker-compose
```

### 2. Clone/Setup Project

```bash
# Create project directory
mkdir -p ~/finance-dashboard
cd ~/finance-dashboard

# Create directory structure
mkdir -p backend nginx certs

# Copy all files from the provided configuration into their directories
# Copy main.py to backend/main.py
# Copy requirements.txt to root
# Copy docker-compose.yml to root
# Copy Dockerfile to root
# Copy nginx.conf to nginx/nginx.conf
```

### 3. Get API Keys (Optional)

For live stock data without rate limiting:

```bash
# Get free Alpha Vantage API key
# Visit: https://www.alphavantage.co/api/#api-key
# Export it as environment variable
export ALPHA_VANTAGE_KEY="your-api-key-here"
```

### 4. Start the Stack

```bash
# Navigate to project directory
cd ~/finance-dashboard

# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Wait ~30 seconds for backend to be ready
sleep 30
```

### 5. Access the Dashboard

**On Local Network:**
```
http://192.168.x.x:80
```

Replace `192.168.x.x` with your Pi's IP address.

**Via VPN:**
Use your VPN IP address instead:
```
http://10.x.x.x:80  (example Wireguard IP)
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# .env
ALPHA_VANTAGE_KEY=your-api-key-here
OLLAMA_HOST=http://ollama:11434
PYTHONUNBUFFERED=1
```

Load it in docker-compose.yml:
```yaml
backend:
  env_file: .env
```

### Ollama Model Selection

By default, Ollama uses `neural-chat`. To use a different model:

1. Access the Ollama container:
```bash
docker exec -it finance-ollama ollama pull mistral  # or another model
```

2. Update backend `main.py`:
```python
# Change this line in get_ollama_insight():
"model": "mistral",  # Change from neural-chat
```

3. Restart backend:
```bash
docker-compose restart backend
```

### API Rate Limits

Free Alpha Vantage API:
- 5 requests/minute
- 100 requests/day

For production:
1. Get an API key from https://www.alphavantage.co/
2. Set `ALPHA_VANTAGE_KEY` environment variable
3. Implement caching (already built-in, 1 hour default)

## VPN Access Setup

### Option 1: Wireguard (Recommended)

1. **Install Wireguard on Pi:**
```bash
sudo apt-get install wireguard wireguard-tools
```

2. **Generate keys:**
```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

3. **Create config** (`/etc/wireguard/wg0.conf`):
```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <your-private-key>

# Add clients below
[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32
```

4. **Enable Wireguard:**
```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

5. **Forward to dashboard:**
Access the dashboard at `http://10.0.0.1` (or your VPN IP) from any connected VPN client.

### Option 2: Tailscale (Easiest)

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate
sudo tailscale up

# Your Pi gets a Tailscale IP (e.g., 100.x.x.x)
# Access from any device: http://100.x.x.x
```

## Monitoring & Maintenance

### Check Service Status

```bash
# View all container status
docker-compose ps

# Check backend logs
docker-compose logs backend -f

# Check Ollama status
docker-compose logs ollama -f
```

### Restart Services

```bash
# Restart everything
docker-compose restart

# Restart specific service
docker-compose restart backend

# Full restart (stop and remove containers)
docker-compose down
docker-compose up -d
```

### Performance Tuning

**For Pi with limited resources:**

1. **Reduce Ollama memory usage:**
```bash
docker exec finance-ollama ollama pull neural-chat:7b-q4_0
# Use quantized versions
```

2. **Increase API cache duration:**
Edit `backend/main.py`:
```python
CACHE_DURATION = 7200  # 2 hours instead of 1
```

3. **Limit background tasks:**
Edit `docker-compose.yml`:
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 512M
```

### Auto-restart on Boot

```bash
# Enable Docker daemon
sudo systemctl enable docker

# Docker Compose will start on boot if configured:
docker-compose up -d  # Creates restart: unless-stopped
```

To manually set boot startup:
```bash
cd ~/finance-dashboard
sudo crontab -e

# Add this line:
@reboot cd /home/pi/finance-dashboard && docker-compose up -d
```

## API Endpoints Reference

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Stock Data with AI Insight
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "type": "stock"}'
```

### Get Crypto Data
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "bitcoin", "type": "crypto"}'
```

### Portfolio Summary
```bash
curl "http://localhost:8000/api/portfolio/summary?symbols=AAPL,BTC,ETH"
```

### List Ollama Models
```bash
curl http://localhost:8000/api/ollama/models
```

## Troubleshooting

### Dashboard shows "API Offline"

1. Check backend is running:
```bash
docker-compose logs backend
```

2. Check port accessibility:
```bash
curl http://localhost:8000/health
```

3. Restart backend:
```bash
docker-compose restart backend
```

### Ollama shows "Offline"

1. Check Ollama container:
```bash
docker-compose logs ollama
```

2. Verify connectivity:
```bash
docker exec finance-ollama curl http://localhost:11434/api/tags
```

3. Restart Ollama:
```bash
docker-compose restart ollama
```

### High CPU Usage

1. Check if Ollama is running inference:
```bash
docker stats finance-ollama
```

2. Reduce model size or frequency of AI requests

3. Limit Docker resources in compose file

### Network Access Issues

1. **Verify Pi IP:**
```bash
hostname -I
```

2. **Test local network access:**
```bash
# From another device on network
curl http://<pi-ip>:80/health
```

3. **Check firewall:**
```bash
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
```

4. **For VPN issues:**
- Verify VPN tunnel is active
- Check routing table: `ip route`
- Verify Pi firewall allows VPN traffic

## Security Considerations

### Local Network Only (Default)
The Nginx config restricts access to local network ranges:
- 192.168.0.0/16
- 10.0.0.0/8
- 172.16.0.0/12

### For VPN Access
- Wireguard provides end-to-end encryption
- Tailscale adds extra security layer
- Both are much safer than exposing to public internet

### API Keys
- Never commit API keys to version control
- Use environment variables
- Rotate keys periodically

### HTTPS Setup (Optional)

Generate self-signed certificate:
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem \
  -out certs/cert.pem -days 365 -nodes
```

Enable in `nginx.conf` (uncomment HTTPS section).

## Customization

### Add More Financial Data Sources

1. **Yahoo Finance:**
```python
# In backend/main.py
async def fetch_etf_data(symbol: str):
    # Implement Yahoo Finance integration
    pass
```

2. **Crypto watchlist:**
```python
# Modify crypto fetch to support multiple formats
CRYPTO_ALIASES = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana"
}
```

3. **Mutual funds:**
```python
# Add mutual fund API integration
async def fetch_mutual_fund_data(symbol: str):
    # Implement mutual fund data fetching
    pass
```

### Custom Dashboard Views

Edit `frontend_Dashboard.jsx`:
- Add portfolio analysis views
- Create price alerts
- Build custom charts
- Add portfolio performance tracking

## Backup and Recovery

### Backup Data
```bash
# Backup Ollama models
docker run --volumes-from finance-ollama \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/ollama.tar.gz -C /root/.ollama .

# Backup cache
docker cp finance-ollama:/tmp/finance_cache ./backups/
```

### Recovery
```bash
# Restore Ollama models
docker run --volumes-from finance-ollama \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/ollama.tar.gz -C /root/.ollama
```

## Advanced Configuration

### Kubernetes Deployment (For multiple Pi cluster)

Create `k8s-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: finance-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: finance-dashboard
  template:
    metadata:
      labels:
        app: finance-dashboard
    spec:
      containers:
      - name: backend
        image: finance-dashboard:latest
        ports:
        - containerPort: 8000
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
```

### Load Balancing Multiple Pi Devices

Set up Nginx load balancing across multiple backends.

## Support & Logs

### Enable Debug Logging

```bash
# Set environment variable
export DEBUG=true

# Check logs
docker-compose logs -f --tail=100
```

### Export Logs
```bash
# Save all logs to file
docker-compose logs > dashboard-logs.txt

# View specific container
docker-compose logs backend > backend-logs.txt
```

## Cost Analysis

**Monthly costs:**
- Raspberry Pi 5 (one-time): $80
- 1TB SSD (one-time): $100
- Electricity (~5W avg): ~$0.50/month
- Internet (existing): $0/month
- APIs: Free tier adequate for personal use

**Total: ~$0.50/month operational cost**

## Next Steps

1. ✅ Set up on Pi
2. 🔄 Configure VPN access
3. 📊 Add custom data sources
4. 🤖 Fine-tune Ollama models
5. 📈 Create advanced analytics views
6. 🔔 Set up price alerts

---

**Enjoy your personal finance dashboard! 📈**
