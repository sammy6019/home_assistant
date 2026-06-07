# Thermostat Monitor

## Purpose
AI monitor for Nest thermostat via HA REST API
Prevents wife setting 64°F during Sam's work hours (8am-5pm weekdays)

## Key entities
- climate.living_room
- HA token: loaded from /mnt/ssd/thermostat/.env

## Rules
- Work hours: 8am-5pm Mon-Fri
- Work temp: 70°F
- Night temp: 64°F (do not override)
- Grace period: 30 min before adjusting
- Always notify before changing
- Log to /mnt/ssd/thermostat/thermostat.log

