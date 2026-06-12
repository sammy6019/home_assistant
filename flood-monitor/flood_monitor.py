import os
import json
import base64
import requests
import anthropic
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo('America/Chicago')
import logging
import time

# ── Configuration ────────────────────────────────────────────────────────────
HA_URL = 'http://192.168.1.227:8123'
SNAPSHOT_DIR = '/mnt/ssd/flood-monitor/snapshots'
LOG_DIR = '/mnt/ssd/flood-monitor/logs'
LOG_FILE = f'{LOG_DIR}/flood_monitor.log'
SNAPSHOT_RETENTION_DAYS = 30
ALERT_COOLDOWN_MINUTES = 30
COOLDOWN_FILE = f'{LOG_DIR}/.last_alert'

# Load tokens from environment or .env file
HA_TOKEN = os.environ.get('HA_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not HA_TOKEN or not ANTHROPIC_API_KEY:
    try:
        with open('/mnt/ssd/flood-monitor/.env') as f:
            for line in f:
                k, _, v = line.strip().partition('=')
                if k == 'HA_TOKEN' and not HA_TOKEN:
                    HA_TOKEN = v
                elif k == 'ANTHROPIC_API_KEY' and not ANTHROPIC_API_KEY:
                    ANTHROPIC_API_KEY = v
    except Exception as e:
        print(f'Warning: Failed to load .env: {e}')

# Primary ditch camera (Ring) — analyzed every run
PRIMARY_CAMERA = {
    'entity': 'camera.garden_live_view',
    'name': 'ditch'
}

# Vivint area cameras — snapshot only, captured when water above first line
VIVINT_CAMERAS = [
    {'entity': 'camera.doorbell', 'name': 'doorbell'},
    {'entity': 'camera.backyard', 'name': 'backyard'},
    {'entity': 'camera.driveway', 'name': 'driveway'},
]

# ── Logging ──────────────────────────────────────────────────────────────────
class LocalTimezoneFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, tz=CHICAGO)
        return ct.strftime('%Y-%m-%d %H:%M:%S %Z')

handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(LocalTimezoneFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ── Snapshot ─────────────────────────────────────────────────────────────────
def get_snapshot(entity_id, label):
    """Grab snapshot from any HA camera via camera_proxy.
    For Vivint cameras, first trigger a snapshot service call to wake the cloud
    stream, then immediately fetch via proxy."""
    try:
        timestamp = datetime.now(CHICAGO).strftime('%Y%m%d_%H%M%S')
        snapshot_path = f'{SNAPSHOT_DIR}/snapshot_{label}_{timestamp}.jpg'

        if entity_id != PRIMARY_CAMERA['entity']:
            # Wake the Vivint cloud stream before fetching
            requests.post(
                f'{HA_URL}/api/services/camera/snapshot',
                headers={
                    'Authorization': f'Bearer {HA_TOKEN}',
                    'Content-Type': 'application/json'
                },
                json={
                    'entity_id': entity_id,
                    'filename': f'/tmp/vivint_wake_{label}.jpg'
                },
                timeout=30
            )
            time.sleep(5)

        img_response = requests.get(
            f'{HA_URL}/api/camera_proxy/{entity_id}',
            headers={'Authorization': f'Bearer {HA_TOKEN}'},
            timeout=30
        )

        if img_response.status_code != 200:
            logging.error(f'[{label}] Snapshot failed: {img_response.status_code} - {img_response.text[:200]}')
            return None

        if 'image' not in img_response.headers.get('Content-Type', ''):
            logging.error(f'[{label}] Unexpected content type: {img_response.headers.get("Content-Type")}')
            return None

        with open(snapshot_path, 'wb') as f:
            f.write(img_response.content)

        logging.info(f'[{label}] Snapshot saved: {snapshot_path}')
        return snapshot_path

    except requests.exceptions.Timeout:
        logging.error(f'[{label}] Timeout connecting to Home Assistant')
        return None
    except Exception as e:
        logging.error(f'[{label}] Error getting snapshot: {e}')
        return None

# ── Snapshot Cleanup ──────────────────────────────────────────────────────────
def cleanup_old_snapshots():
    """Remove snapshots older than SNAPSHOT_RETENTION_DAYS."""
    cutoff = time.time() - (SNAPSHOT_RETENTION_DAYS * 86400)
    removed = 0
    try:
        for fname in os.listdir(SNAPSHOT_DIR):
            fpath = os.path.join(SNAPSHOT_DIR, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        if removed:
            logging.info(f'Cleaned up {removed} snapshots older than {SNAPSHOT_RETENTION_DAYS} days')
    except Exception as e:
        logging.warning(f'Snapshot cleanup failed: {e}')

# ── Claude Vision Analysis ────────────────────────────────────────────────────
def analyze_ditch(image_path):
    """Analyze ditch image for water level vs fluorescent orange numbered markers."""
    prompt = """You are a flood detection system analyzing a drainage ditch camera image.
    This may be a nighttime or low-light image.

WATER LEVEL MARKERS:
- There is a stake or root with 3 fluorescent orange horizontal bands numbered 1, 2, 3 bottom to top
- There is a corrugated drainage pipe at the bottom right

CRITICAL RULES — READ CAREFULLY:
- You MUST be able to clearly see the orange numbered markers to make any assessment
- If the image is too dark to clearly see the markers, report LEVEL: none
- Wet soil, mud, puddles on soil, and damp ground are NOT flooding — ignore these completely
- Shadows and dark patches are NOT water
- Reflections on leaves or vegetation are NOT water
- Water MUST be a clearly visible body of standing liquid filling the ditch basin
- If you have ANY doubt whether water is present, report LEVEL: none
- Only report medium/high/critical if water is UNAMBIGUOUSLY visible above the ditch floor

NIGHTTIME RULE:
- If this is a dark or nighttime image and you cannot clearly confirm water AND see the markers,
  you MUST report LEVEL: none regardless of what you think you see

FLOOD LEVELS:
- none: markers not visible OR no water visible OR uncertain
- low: water clearly visible but below marker 1
- medium: water clearly at or covering marker 1
- high: water clearly at or covering marker 2
- critical: water clearly at marker 3 or above, or pipe fully submerged

ANSWER FORMAT:
Start with: LEVEL: (none/low/medium/high/critical)
1. Can you clearly see the fluorescent orange numbered markers? yes or no
2. Is the image dark or nighttime? yes or no
3. Is there UNAMBIGUOUS standing water filling the ditch? yes or no
4. If yes, which marker is water at or above?
5. Is the drainage pipe submerged? yes or no"""

    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logging.error(f'Failed to read image for analysis: {e}')
        return None

    last_error = None
    for attempt in range(2):
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=512,
                messages=[{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': image_data,
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }]
            )
            analysis = message.content[0].text.strip()
            logging.info(f'Analysis: {analysis}')
            return analysis
        except Exception as e:
            last_error = e
            logging.warning(f'Claude API attempt {attempt + 1} failed: {e}')
            if attempt < 1:
                time.sleep(5)

    logging.error(f'Claude API failed after 2 attempts: {last_error}')
    return None

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_level(analysis):
    """Extract flood level from analysis text."""
    if not analysis:
        return 'unknown'
    lower = analysis.lower()
    for level in ['critical', 'high', 'medium', 'low', 'none']:
        if f'level: {level}' in lower:
            return level
    return 'unknown'

def _markers_visible(lower):
    """Return True if the model confirmed markers were visible."""
    # Look for the structured answer to question 1
    for phrase in ('markers? yes', 'numbered markers? yes', 'see the fluorescent orange numbered markers? yes'):
        if phrase in lower:
            return True
    for phrase in ('markers? no', 'numbered markers? no', 'see the fluorescent orange numbered markers? no'):
        if phrase in lower:
            return False
    # Ambiguous — treat as not visible to be safe
    return False

def _is_nighttime(lower):
    """Return True if the model flagged the image as dark/nighttime."""
    return 'dark or nighttime? yes' in lower or 'nighttime? yes' in lower

def check_flood_alert(analysis):
    """Only alert on high/critical with confirmed marker visibility and daytime image."""
    if not analysis:
        return False
    lower = analysis.lower()
    level = parse_level(analysis)
    if level not in ['high', 'critical']:
        return False
    if not _markers_visible(lower):
        logging.warning('Suppressed alert — markers not confirmed visible')
        return False
    if _is_nighttime(lower):
        logging.warning('Suppressed alert — nighttime image, insufficient confidence')
        return False
    return True

def above_first_line(analysis):
    """Trigger Vivint capture only if markers visible, daytime, and water confirmed."""
    if not analysis:
        return False
    lower = analysis.lower()
    level = parse_level(analysis)
    if level not in ['medium', 'high', 'critical']:
        return False
    if not _markers_visible(lower) or _is_nighttime(lower):
        return False
    return True

# ── Alert Cooldown ────────────────────────────────────────────────────────────
def is_within_cooldown():
    """Return True if an alert was sent recently (within ALERT_COOLDOWN_MINUTES)."""
    try:
        if not os.path.exists(COOLDOWN_FILE):
            return False
        last = float(open(COOLDOWN_FILE).read().strip())
        elapsed = (time.time() - last) / 60
        if elapsed < ALERT_COOLDOWN_MINUTES:
            logging.info(f'Alert suppressed — cooldown active ({elapsed:.0f}/{ALERT_COOLDOWN_MINUTES} min)')
            return True
    except Exception:
        pass
    return False

def record_alert_sent():
    try:
        with open(COOLDOWN_FILE, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        logging.warning(f'Failed to write cooldown file: {e}')

# ── Notification ──────────────────────────────────────────────────────────────
def send_ha_notification(message):
    """Send push notification via Home Assistant. Returns True on success."""
    try:
        resp = requests.post(
            f'{HA_URL}/api/services/notify/mobile_app_iphone',
            headers={
                'Authorization': f'Bearer {HA_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'title': '🚨 Flood Alert - Ditch Monitor',
                'message': message
            },
            timeout=15
        )
        if resp.status_code not in (200, 201):
            logging.error(f'Notification failed: HTTP {resp.status_code}')
            return False
        logging.info('Flood alert notification sent')
        return True
    except Exception as e:
        logging.error(f'Error sending notification: {e}')
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def run_monitor():
    """Main monitoring function."""
    logging.info('Starting flood monitor check')

    cleanup_old_snapshots()

    # ── Step 1: Ditch camera — always runs ──────────────────────
    logging.info('Grabbing ditch snapshot...')
    ditch_snapshot = get_snapshot(PRIMARY_CAMERA['entity'], PRIMARY_CAMERA['name'])

    if not ditch_snapshot:
        logging.error('Aborting — could not get ditch snapshot')
        return

    logging.info('Analyzing ditch image...')
    analysis = analyze_ditch(ditch_snapshot)

    if not analysis:
        logging.error('Aborting — could not analyze ditch image')
        return

    level = parse_level(analysis)
    alert = check_flood_alert(analysis)
    logging.info(f'Level: {level} | Alert: {alert}')

    # ── Step 2: Vivint cameras — only if above marker 1 ─────────
    vivint_snapshots = {}

    if above_first_line(analysis):
        logging.info(f'Water above marker 1 ({level}) — capturing Vivint cameras...')
        for cam in VIVINT_CAMERAS:
            path = None
            path = get_snapshot(cam['entity'], cam['name'])
            if path:
                vivint_snapshots[cam['name']] = path
            else:
                logging.error(f'[{cam["name"]}] Snapshot failed, skipping')
    else:
        logging.info(f'Level is {level} — below marker 1, skipping Vivint cameras')

    # ── Step 3: Send alert if needed ────────────────────────────
    if alert:
        if is_within_cooldown():
            logging.info('Alert suppressed by cooldown')
        else:
            lines = ['⚠️ Flood detected at ditch!\n']
            lines.append(f'📊 Level: {level.upper()}')
            lines.append(f'{analysis[:200]}\n')
            if vivint_snapshots:
                lines.append(f'📷 Area snapshots captured: {", ".join(vivint_snapshots.keys())}')
            if send_ha_notification('\n'.join(lines)):
                record_alert_sent()
            logging.warning(f'FLOOD ALERT SENT — level: {level}')
    else:
        logging.info('No flooding detected — all clear')

    # ── Step 4: Write log entry ──────────────────────────────────
    log_entry = {
        'timestamp': datetime.now(CHICAGO).isoformat(),
        'snapshot': ditch_snapshot,
        'analysis': analysis,
        'flood_detected': alert,
        'level': level,
        'vivint_snapshots': vivint_snapshots
    }
    with open(f'{LOG_DIR}/history.json', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    logging.info(f'Monitor check complete. Level: {level} | Vivint snapshots: {len(vivint_snapshots)}')


if __name__ == '__main__':
    run_monitor()
