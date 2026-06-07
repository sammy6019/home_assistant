# Homelab — Raspberry Pi 5

## Stack
- OS: Raspberry Pi OS (Debian)
- Python 3.11
- Docker + Portainer
- Home Assistant at http://192.168.1.227:8123
- Ollama at http://localhost:11434 (llava model)
- Domain: ollamapi.com via Cloudflare tunnel

## Project paths
- Flood monitor: /mnt/ssd/flood-monitor/
- HA config: /mnt/ssd/homeassistant/config/
- Thermostat: /mnt/ssd/thermostat/
- Web (nginx): /mnt/ssd/flood-monitor/webapp/

## Conventions
- Tokens from .env file, never hardcoded
- Logging uses CST timezone
- All scripts follow flood_monitor.py patterns
- pip installs use --break-system-packages
- Docker uses host network mode

## HA entities we use
- climate.living_room (Nest thermostat)
- camera.garden_live_view (Ring ditch)
- camera.doorbell, camera.backyard, camera.driveway (Vivint)
- weather.forecast_home

## Do not edit
- /mnt/ssd/flood-monitor/logs/history.json directly
- Any Docker container configs without noting changes
