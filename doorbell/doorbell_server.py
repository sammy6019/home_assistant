import os
import io
import json
import base64
import logging
import requests
import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify
from PIL import Image

CHICAGO = ZoneInfo('America/Chicago')
HA_URL = 'http://192.168.1.227:8123'
CAPTURE_DIR = '/mnt/ssd/doorbell/captures'
LOG_FILE = '/mnt/ssd/doorbell/logs/doorbell.log'
LAST_CAPTURE_FILE = '/mnt/ssd/homeassistant/www/doorbell_last.jpg'
MAX_IMAGE_PX = 1024

HA_TOKEN = os.environ.get('HA_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not HA_TOKEN or not ANTHROPIC_API_KEY:
    try:
        with open('/mnt/ssd/doorbell/.env') as f:
            for line in f:
                k, _, v = line.strip().partition('=')
                if k == 'HA_TOKEN' and not HA_TOKEN:
                    HA_TOKEN = v
                elif k == 'ANTHROPIC_API_KEY' and not ANTHROPIC_API_KEY:
                    ANTHROPIC_API_KEY = v
    except Exception as e:
        print(f'Warning: Failed to load .env: {e}')

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

class LocalTimezoneFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, tz=CHICAGO)
        return ct.strftime('%Y-%m-%d %H:%M:%S %Z')

handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(LocalTimezoneFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())

app = Flask(__name__)


def compress_image(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    if max(img.size) > MAX_IMAGE_PX:
        img.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=85)
    return out.getvalue()


def classify_visitor(image_bytes: bytes) -> str:
    today = datetime.now(CHICAGO)
    is_halloween = (today.month == 10 and today.day == 31)

    prompt = (
        "Analyze this image from a doorbell camera. "
        "Respond with ONLY one word from this list:\n"
        "BUSINESS - if the person is wearing business attire (suit, uniform) AND has a visible company logo, briefcase, or sales materials\n"
        f"HALLOWEEN_KIDS - if children are in costumes AND today is October 31 (Halloween) [today is {'Oct 31' if is_halloween else 'NOT Oct 31'}]\n"
        "ANIMAL - if the subject is a non-human animal (dog, cat, raccoon, deer, etc.)\n"
        "VISITOR - for everyone else (delivery person, friend, family, regular visitor)\n\n"
        "Respond with exactly ONE word only."
    )

    compressed = compress_image(image_bytes)
    image_data = base64.b64encode(compressed).decode('utf-8')

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for attempt in range(2):
        try:
            message = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=10,
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
                        {'type': 'text', 'text': prompt}
                    ]
                }]
            )
            result = message.content[0].text.strip().upper()
            valid = {'BUSINESS', 'HALLOWEEN_KIDS', 'ANIMAL', 'VISITOR'}
            for v in valid:
                if v in result:
                    return v
            logger.warning(f'Unexpected classification: {result}, defaulting to VISITOR')
            return 'VISITOR'
        except Exception as e:
            logger.warning(f'Claude API attempt {attempt + 1} failed: {e}')
            if attempt == 0:
                import time; time.sleep(3)

    logger.error('Claude API failed after 2 attempts, defaulting to VISITOR')
    return 'VISITOR'


def ha_call(service_domain, service, data):
    try:
        resp = requests.post(
            f'{HA_URL}/api/services/{service_domain}/{service}',
            headers={'Authorization': f'Bearer {HA_TOKEN}', 'Content-Type': 'application/json'},
            json=data,
            timeout=15
        )
        if resp.status_code not in (200, 201):
            logger.error(f'HA service call failed: {resp.status_code} {resp.text[:200]}')
            return False
        return True
    except Exception as e:
        logger.error(f'HA service call error: {e}')
        return False


def trigger_response(classification: str, capture_path: str):
    if classification == 'BUSINESS':
        logger.info('BUSINESS visitor — playing TTS rejection')
        ha_call('tts', 'speak', {
            'entity_id': 'tts.home_assistant_cloud',
            'media_player_entity_id': 'media_player.doorbell',
            'message': 'Sorry, not interested in sales. Please leave.',
        })

    elif classification == 'HALLOWEEN_KIDS':
        logger.info('HALLOWEEN_KIDS — playing trick-or-treat TTS')
        ha_call('tts', 'speak', {
            'entity_id': 'tts.home_assistant_cloud',
            'media_player_entity_id': 'media_player.doorbell',
            'message': 'Nice costume! Enjoy trick-or-treating!',
        })

    elif classification == 'ANIMAL':
        logger.info('ANIMAL detected — playing scary sound')
        ha_call('media_player', 'play_media', {
            'entity_id': 'media_player.doorbell',
            'media_content_id': 'media-source://media_source/local/scary_sound.mp3',
            'media_content_type': 'audio/mp3',
        })

    elif classification == 'VISITOR':
        logger.info('VISITOR — sending silent phone notification with image')
        # Encode capture as base64 for notification (HA mobile app supports image URLs)
        ha_call('notify', 'mobile_app_iphone', {
            'title': 'Doorbell',
            'message': f'Someone at the door — {datetime.now(CHICAGO).strftime("%I:%M %p")}',
            'data': {
                'push': {'sound': 'none'},
                'image': f'/local/doorbell_last.jpg',
            }
        })

    # Fire HA event for binary_sensor / automation trigger
    ha_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.doorbell_active'})


@app.route('/doorbell', methods=['POST'])
def doorbell_webhook():
    logger.info('Doorbell webhook received')

    if 'image' not in request.files and not request.data:
        # Try to grab snapshot from HA camera directly
        try:
            img_resp = requests.get(
                f'{HA_URL}/api/camera_proxy/camera.doorbell',
                headers={'Authorization': f'Bearer {HA_TOKEN}'},
                timeout=30
            )
            if img_resp.status_code != 200 or 'image' not in img_resp.headers.get('Content-Type', ''):
                logger.error('Failed to get doorbell snapshot from HA')
                return jsonify({'error': 'no image'}), 400
            image_bytes = img_resp.content
        except Exception as e:
            logger.error(f'Failed to fetch HA camera snapshot: {e}')
            return jsonify({'error': str(e)}), 500
    elif 'image' in request.files:
        image_bytes = request.files['image'].read()
    else:
        image_bytes = request.data

    # Save timestamped capture
    timestamp = datetime.now(CHICAGO).strftime('%Y%m%d_%H%M%S')
    capture_path = f'{CAPTURE_DIR}/capture_{timestamp}.jpg'
    with open(capture_path, 'wb') as f:
        f.write(image_bytes)

    # Save as last capture for HA dashboard (symlink-style overwrite)
    with open(LAST_CAPTURE_FILE, 'wb') as f:
        f.write(image_bytes)

    logger.info(f'Saved capture: {capture_path}')

    classification = classify_visitor(image_bytes)
    logger.info(f'Classification: {classification}')

    trigger_response(classification, capture_path)

    # Log event
    event = {
        'timestamp': datetime.now(CHICAGO).isoformat(),
        'capture': capture_path,
        'classification': classification,
    }
    with open('/mnt/ssd/doorbell/logs/history.json', 'a') as f:
        f.write(json.dumps(event) + '\n')

    return jsonify({'status': 'ok', 'classification': classification})


@app.route('/doorbell/last', methods=['GET'])
def last_capture():
    """Return last capture metadata for HA dashboard."""
    try:
        history_file = '/mnt/ssd/doorbell/logs/history.json'
        if not os.path.exists(history_file):
            return jsonify({'classification': 'none', 'timestamp': None})
        with open(history_file) as f:
            lines = f.readlines()
        if not lines:
            return jsonify({'classification': 'none', 'timestamp': None})
        last = json.loads(lines[-1])
        return jsonify(last)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    logger.info('Doorbell AI server starting on port 5001')
    app.run(host='0.0.0.0', port=5001)
