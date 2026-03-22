import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "claude_analytics")
POSTGRES_USER = os.getenv("POSTGRES_USER", "analytics")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "analytics")
DATA_DIR = os.getenv("DATA_DIR", "output")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
