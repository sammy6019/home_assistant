import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'arxiv_papers'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
}

BASE_DIR = Path(__file__).resolve().parent.parent

ARXIV_MAX_RESULTS = int(os.getenv('ARXIV_MAX_RESULTS', '100'))
ARXIV_RATE_LIMIT = float(os.getenv('ARXIV_RATE_LIMIT', '3'))

EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', '32'))
EMBEDDING_DEVICE = os.getenv('EMBEDDING_DEVICE', 'cpu')

PDF_STORAGE_PATH = (BASE_DIR / os.getenv('PDF_STORAGE_PATH', './data/pdfs')).resolve()
CACHE_PATH = (BASE_DIR / os.getenv('CACHE_PATH', './data/cache')).resolve()
LOG_PATH = (BASE_DIR / os.getenv('LOG_PATH', './data/logs')).resolve()

for _path in (PDF_STORAGE_PATH, CACHE_PATH, LOG_PATH):
    _path.mkdir(parents=True, exist_ok=True)
