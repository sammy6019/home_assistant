# Home Lab Rules

## Key Directories
- `/mnt/ssd/homeassistant/` - Home Assistant config
- `/mnt/ssd/flood-monitor/` - Flood monitoring system
- `/mnt/ssd/logs/` - Application logs

## Do Not Edit Without Permission
- `.storage/` (HA database)
- `.ollama/` (model cache)
- Any database files

## Context-Aware
- Explicit file reads only (don't glob large dirs)
- Use grep/find to filter logs before reading
- When unsure, ask before reading files >1MB
