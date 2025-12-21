import os
import tempfile
from pathlib import Path

# Where temporary builds happen
BUILD_ROOT = Path(tempfile.gettempdir()) / "latex_builds"
BUILD_ROOT.mkdir(exist_ok=True)

# Optional local output folder (kept for debugging/backward compatibility)
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

# MinIO / S3-compatible storage configuration
# Default to localhost:9100 for local non-compose runs; in compose we use http://minio:9000
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9100")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "latex-builds")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_REGION = os.getenv("MINIO_REGION") or None
PDF_URL_TTL_SECONDS = int(os.getenv("PDF_URL_TTL_SECONDS", "3600"))

# Compile constraints
LATEX_TIMEOUT_SECONDS = int(os.getenv("LATEX_TIMEOUT_SECONDS", "30"))
MAX_CONCURRENT_COMPILES = int(os.getenv("MAX_CONCURRENT_COMPILES", "4"))
MAX_LATEX_BYTES = int(os.getenv("MAX_LATEX_BYTES", str(1_000_000)))  # 1 MB default
KEEP_LOCAL_OUTPUT = os.getenv("KEEP_LOCAL_OUTPUT", "false").lower() == "true"
