import os
import glob
from datetime import datetime, timedelta
import logging

LOG_DIR = '/mnt/ssd/flood-monitor/logs'
SNAPSHOT_DIR = '/mnt/ssd/flood-monitor/snapshots'
LOG_FILE = f'{LOG_DIR}/flood_monitor.log'

# How many days to keep snapshots
KEEP_DAYS = 30

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def cleanup_snapshots():
    """Delete snapshots older than KEEP_DAYS"""
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    snapshots = glob.glob(f'{SNAPSHOT_DIR}/*.jpg')
    
    deleted = 0
    kept = 0
    freed = 0

    for path in snapshots:
        try:
            modified = datetime.fromtimestamp(os.path.getmtime(path))
            if modified < cutoff:
                size = os.path.getsize(path)
                os.remove(path)
                freed += size
                deleted += 1
            else:
                kept += 1
        except Exception as e:
            logging.error(f'Error deleting {path}: {e}')

    freed_mb = freed / (1024 * 1024)
    logging.info(f'Cleanup complete. Deleted: {deleted} | Kept: {kept} | Freed: {freed_mb:.1f} MB')
    print(f'Cleanup complete. Deleted: {deleted} | Kept: {kept} | Freed: {freed_mb:.1f} MB')

if __name__ == '__main__':
    cleanup_snapshots()
