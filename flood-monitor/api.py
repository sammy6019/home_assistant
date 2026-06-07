import json
import subprocess
import threading
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler

monitor_state = {'running': False}

def run_monitor_bg():
    try:
        subprocess.run(
            ['python3', '/mnt/ssd/flood-monitor/weather_check.py'],
            timeout=600
        )
    except Exception as e:
        print(f'Monitor run error: {e}')
    finally:
        monitor_state['running'] = False

class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # ── Events ──────────────────────────────────────────────
        if self.path == '/api/events':
            try:
                events = []
                with open('/mnt/ssd/flood-monitor/logs/history.json', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            events.append(json.loads(line))
                self._json(200, events)
            except Exception as e:
                self._json(500, {'error': str(e)})

        # ── Status ───────────────────────────────────────────────
        elif self.path == '/api/status':
            self._json(200, {'running': monitor_state['running']})

        # ── Snapshot image serving ───────────────────────────────
        elif self.path.startswith('/api/snapshot/'):
            filename = self.path[len('/api/snapshot/'):]
            # Security: strip any path traversal attempts
            filename = filename.replace('..', '').replace('/', '')
            filepath = f'/mnt/ssd/flood-monitor/snapshots/{filename}'
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'max-age=3600')
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self._json(404, {'error': 'Snapshot not found'})
            except Exception as e:
                self._json(500, {'error': str(e)})

        else:
            self._json(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path == '/api/trigger':
            if monitor_state['running']:
                self._json(409, {'error': 'Monitor already running'})
                return
            monitor_state['running'] = True
            thread = threading.Thread(target=run_monitor_bg, daemon=True)
            thread.start()
            self._json(200, {'status': 'started'})
