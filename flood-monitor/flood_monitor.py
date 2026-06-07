import os
import json
import base64
import requests
from datetime import datetime
import logging
import time

# ── Configuration ────────────────────────────────────────────────────────────
HA_URL = 'http://192.168.1.227:8123'
SNAPSHOT_DIR = '/mnt/ssd/flood-monitor/snapshots'
LOG_DIR = '/mnt/ssd/flood-monitor/logs'
LOG_FILE = f'{LOG_DIR}/flood_monitor.log'

# Load token from environment or .env file
HA_TOKEN = os.environ.get('HA_TOKEN')
if not HA_TOKEN:
    try:
        with open('/mnt/ssd/flood-monitor/.env') as f:
            for line in f:
                if line.startswith('HA_TOKEN='):
                    HA_TOKEN = line.strip().split('=', 1)[1]
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
import logging
from datetime import timezone, timedelta

class CSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        cst = timezone(timedelta(hours=-6))
        ct = datetime.fromtimestamp(record.created, cst)
        return ct.strftime('%Y-%m-%d %H:%M:%S')

handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(CSTFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ── Snapshot ─────────────────────────────────────────────────────────────────
def get_snapshot(entity_id, label):
    """Grab snapshot from any HA camera"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_path = f'{SNAPSHOT_DIR}/snapshot_{label}_{timestamp}.jpg'

        # For Vivint cameras use the HA snapshot service
        # which forces HA to actively request a frame from the cloud
        if entity_id != PRIMARY_CAMERA['entity']:
            service_response = requests.post(
                f'{HA_URL}/api/services/camera/snapshot',
                headers={
                    'Authorization': f'Bearer {HA_TOKEN}',
                    'Content-Type': 'application/json'
                },
                json={
                    'entity_id': entity_id,
                    'filename': f'/tmp/snapshot_{label}_{timestamp}.jpg'
                },
                timeout=30
            )
            if service_response.status_code not in [200, 201]:
                logging.error(f'[{label}] HA snapshot service failed: {service_response.status_code}')
                # Fall through to camera_proxy as backup
            else:
                # Download the saved file via HA file API
                time.sleep(2)  # Give HA a moment to save it

        # Use camera_proxy for Ring or as fallback
        image_url = f'{HA_URL}/api/camera_proxy/{entity_id}'
        img_response = requests.get(
            image_url,
            headers={'Authorization': f'Bearer {HA_TOKEN}'},
            timeout=30
        )

        if img_response.status_code != 200:
            logging.error(f'[{label}] Snapshot download failed: {img_response.status_code} - {img_response.text[:200]}')
            return None

        content_type = img_response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            logging.error(f'[{label}] Unexpected content type: {content_type}')
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

# ── Ollama Analysis ───────────────────────────────────────────────────────────
def analyze_ditch(image_path):
    """Analyze ditch image for water level vs fluorescent orange numbered markers"""
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

       # Retry up to 2 times with extended timeout
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(
                    'http://localhost:11434/api/generate',
                    json={
                        'model': 'llava',
                        'prompt': prompt,
                        'images': [image_data],
                        'stream': False
                    },
                    timeout=480
                )
                analysis = response.json()['response'].strip()
                logging.info(f'Analysis: {analysis}')
                return analysis
            except Exception as e:
                last_error = e
                logging.warning(f'Ollama attempt {attempt + 1} failed: {e}')
                time.sleep(10)

        logging.error(f'Ollama failed after 2 attempts: {last_error}')
        return None 
        
        analysis = response.json()['response'].strip()
        logging.info(f'Analysis: {analysis}')
        return analysis
    except Exception as e:
        logging.error(f'Error analyzing ditch image: {e}')
        return None

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_level(analysis):
    """Extract flood level from analysis text"""
    if not analysis:
        return 'unknown'
    lower = analysis.lower()
    for level in ['critical', 'high', 'medium', 'low', 'none']:
        if f'level: {level}' in lower:
            return level
    return 'unknown'

def check_flood_alert(analysis):
    """Only alert on high/critical AND markers are confirmed visible"""
    if not analysis:
        return False
    lower = analysis.lower()
    level = parse_level(analysis)
    if level not in ['high', 'critical']:
        return False
    # Don't alert if markers weren't visible
    if 'markers? no' in lower or 'markers? n' in lower:
        logging.warning('Suppressed alert — markers not visible in image')
        return False
    # Don't alert if it was a dark/nighttime image
    if 'nighttime? yes' in lower or 'dark or nighttime? yes' in lower:
        logging.warning('Suppressed alert — nighttime image, insufficient confidence')
        return False
    return True

def above_first_line(analysis):
    """Only trigger Vivint capture if markers visible and water confirmed"""
    if not analysis:
        return False
    lower = analysis.lower()
    level = parse_level(analysis)
    if level not in ['medium', 'high', 'critical']:
        return False
    if 'markers? no' in lower or 'nighttime? yes' in lower or 'dark or nighttime? yes' in lower:
        return False
    return True

# ── Notification ──────────────────────────────────────────────────────────────
def send_ha_notification(message):
    """Send push notification via Home Assistant"""
    try:
        requests.post(
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
        logging.info('Flood alert notification sent!')
    except Exception as e:
        logging.error(f'Error sending notification: {e}')


# ── Main ──────────────────────────────────────────────────────────────────────
def run_monitor():
    """Main monitoring function"""
    logging.info('Starting flood monitor check')
    print(f'[{datetime.now()}] Running flood monitor check...')

    timestamp = datetime.now().isoformat()

    # ── Step 1: Ditch camera — always runs ──────────────────────
    print('Grabbing snapshot: ditch...')
    ditch_snapshot = get_snapshot(PRIMARY_CAMERA['entity'], PRIMARY_CAMERA['name'])

    if not ditch_snapshot:
        print('Failed to get ditch snapshot — aborting')
        logging.error('Aborting — could not get ditch snapshot')
        return

    print('Analyzing ditch image...')
    analysis = analyze_ditch(ditch_snapshot)

    if not analysis:
        print('Failed to analyze ditch image — aborting')
        logging.error('Aborting — could not analyze ditch image')
        return

    level = parse_level(analysis)
    alert = check_flood_alert(analysis)
    print(f'[ditch] Level: {level} | Alert: {alert}')

    # ── Step 2: Vivint cameras — only if above marker 1 ─────────
    vivint_snapshots = {}

    if above_first_line(analysis):
        print(f'Water above marker 1 ({level}) — capturing Vivint cameras...')
        for cam in VIVINT_CAMERAS:
            print(f'Grabbing snapshot: {cam["name"]}...')
            # Retry up to 3 times with delay — Vivint cloud can be slow
            path = None
            for attempt in range(3):
                path = get_snapshot(cam['entity'], cam['name'])
                if path:
                    break
                print(f'[{cam["name"]}] Attempt {attempt + 1} failed, retrying in 10s...')
                time.sleep(10)
            if path:
                vivint_snapshots[cam['name']] = path
                print(f'[{cam["name"]}] Captured')
            else:
                print(f'[{cam["name"]}] Failed after 3 attempts')
    else:
        print(f'Level is {level} — below marker 1, skipping Vivint cameras')

    # ── Step 3: Send alert if needed ────────────────────────────
    if alert:
        lines = ['⚠️ Flood detected at ditch!\n']
        lines.append(f'📊 Level: {level.upper()}')
        lines.append(f'{analysis[:200]}\n')
        if vivint_snapshots:
            lines.append(f'📷 Area snapshots captured: {", ".join(vivint_snapshots.keys())}')
        send_ha_notification('\n'.join(lines))
        print('FLOOD ALERT SENT')
    else:
        print('No flooding detected - all clear')

    # ── Step 4: Write log entry ──────────────────────────────────
    log_entry = {
        'timestamp': timestamp,
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
