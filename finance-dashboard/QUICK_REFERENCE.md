# 🚀 Quick Reference Guide

## Starting & Stopping

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# View running containers
docker-compose ps

# View logs for specific service
docker-compose logs -f backend

# View all logs
docker-compose logs -f --tail=50
```

## Service Status

```bash
# Check if backend is healthy
curl http://localhost:8000/health

# Check Ollama models
curl http://localhost:11434/api/tags

# List available endpoints
curl http://localhost:8000/docs  # Interactive API docs
```

## Common Tasks

### Add Stock to Portfolio
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "type": "stock"}'
```

### Add Cryptocurrency
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "bitcoin", "type": "crypto"}'
```

### Get Portfolio Summary
```bash
curl "http://localhost:8000/api/portfolio/summary?symbols=AAPL,BTC,ETH,VTI"
```

### List All Ollama Models
```bash
curl http://localhost:8000/api/ollama/models
```

## Ollama Model Management

```bash
# Pull a new model
docker exec finance-ollama ollama pull mistral

# Run model directly
docker exec finance-ollama ollama run mistral "What is Bitcoin?"

# List downloaded models
docker exec finance-ollama ollama list

# Remove a model (free up space)
docker exec finance-ollama ollama rm mistral
```

## Performance & Monitoring

```bash
# Check container resource usage
docker stats

# Check Pi CPU/memory
free -h
df -h
top

# Monitor container logs in real-time
docker-compose logs -f --timestamps

# Check network connectivity
ping 8.8.8.8
curl -I https://api.coingecko.com
```

## Maintenance

```bash
# Clean up Docker images
docker image prune -a

# Clean up volumes (WARNING: removes data!)
docker volume prune

# Backup Ollama models
docker run --volumes-from finance-ollama \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/ollama.tar.gz -C /root/.ollama .

# View disk usage
du -sh backend/
du -sh .

# Check SSD health
sudo smartctl -a /dev/sda  # Replace sda with your drive
```

## Configuration Changes

### Update API Key
```bash
# Edit .env
nano .env

# Add your Alpha Vantage key:
# ALPHA_VANTAGE_KEY=your-key-here

# Restart backend
docker-compose restart backend
```

### Change Ollama Model
```bash
# 1. Pull the model
docker exec finance-ollama ollama pull mistral

# 2. Edit backend/main.py, line ~180:
# Change: "model": "neural-chat"
# To:     "model": "mistral"

# 3. Restart backend
docker-compose restart backend
```

### Increase Cache Duration
```bash
# Edit backend/main.py, line ~35:
CACHE_DURATION = 7200  # Changed from 3600 (2 hours)

# Restart backend
docker-compose restart backend
```

## Networking & VPN

### Find Pi IP Address
```bash
hostname -I
# or
ip addr show | grep "inet "
```

### Test Local Network Access
```bash
# From another device on network
curl http://192.168.x.x:80/health
```

### Setup Port Forwarding (if needed)
```bash
# For external access (NOT recommended - use VPN instead)
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Check VPN Connection
```bash
# For Wireguard
sudo wg show

# For Tailscale
tailscale status

# Check local network connections
netstat -tlnp | grep LISTEN
```

## Troubleshooting Quick Fixes

### Services won't start
```bash
# Check disk space
df -h
# Might need to clean up Docker images

# Verify compose file syntax
docker-compose config

# Check system logs
journalctl -xe
```

### API returning errors
```bash
# Check backend logs
docker-compose logs backend -f

# Check API connectivity
curl -v http://localhost:8000/health

# Restart backend
docker-compose restart backend
```

### Ollama slow or not responding
```bash
# Check Ollama logs
docker-compose logs ollama -f

# Check if model is downloading
docker stats finance-ollama

# Restart Ollama
docker-compose restart ollama
```

### High CPU/Memory usage
```bash
# Check what's using resources
docker stats

# Check system memory
free -h

# Monitor Ollama specifically
docker exec finance-ollama top
```

### Network access issues
```bash
# Test local network
ping 192.168.x.x

# Test internet
ping 8.8.8.8

# Check DNS
nslookup api.coingecko.com

# Test specific API
curl -I https://api.coingecko.com/api/v3/simple/price
```

## Useful Links

- **Backend API Docs**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc
- **Alpha Vantage API**: https://www.alphavantage.co/
- **CoinGecko API**: https://www.coingecko.com/en/api/documentation
- **Ollama Models**: https://ollama.ai/library

## Environment Variables Quick Reference

```bash
# View current environment
docker-compose exec backend printenv | grep -E "(ALPHA|OLLAMA|PYTHON)"

# Set temporary env var
docker-compose exec backend bash -c 'export DEBUG=true && python main.py'
```

## Emergency Commands

```bash
# Nuclear option - restart everything
docker-compose down -v
docker-compose up -d
docker-compose logs -f

# Remove everything and start fresh
docker-compose down -v
docker system prune -a
docker-compose up -d

# Check if port is already in use
sudo lsof -i :8000
sudo lsof -i :80

# Kill process on port (if needed)
sudo kill -9 <PID>
```

## Performance Tips

```bash
# Check if Ollama is using too much memory
docker exec finance-ollama top

# Reduce memory usage - use smaller model
docker exec finance-ollama ollama pull orca-mini

# Add resource limits in docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       cpus: '2'
#       memory: 512M
```

## System Information

```bash
# Check Pi model and specs
cat /proc/device-tree/model
lscpu

# Check Raspberry Pi CPU temperature
vcgencmd measure_temp

# Check disk speed (useful for SSD)
sudo hdparm -tT /dev/sda1

# Check Ubuntu/Raspbian version
lsb_release -a
uname -a
```

## One-Liners

```bash
# Quick health check
for service in backend ollama nginx; do echo "$service:" && docker-compose logs $service --tail=5 | head -2; done

# Monitor all services in real-time
watch -n 1 'docker-compose ps && echo "---" && docker stats --no-stream'

# Get all logs since last restart
docker-compose logs --since 1m

# Backup configuration
tar -czf dashboard-backup-$(date +%Y%m%d).tar.gz . --exclude=node_modules --exclude=__pycache__ --exclude=.git

# Find all running Python processes
ps aux | grep python

# Count API requests (from logs)
docker-compose logs | grep "api" | wc -l
```

---

**Need more help?** Check [SETUP_GUIDE.md](SETUP_GUIDE.md) or [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
