import shutil
import subprocess
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from .config import (
    BUILD_ROOT,
    KEEP_LOCAL_OUTPUT,
    LATEX_TIMEOUT_SECONDS,
    MAX_LATEX_BYTES,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_REGION,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    OUTPUT_DIR,
    PDF_URL_TTL_SECONDS,
)


_minio_client = None
_bucket_ready = False


def _normalized_endpoint(endpoint: str, secure_flag: bool):
    parsed = urlparse(endpoint)
    if parsed.scheme:
        secure_from_scheme = parsed.scheme == "https"
        return parsed.netloc, (secure_from_scheme or secure_flag)
    return endpoint, secure_flag


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        endpoint, secure = _normalized_endpoint(MINIO_ENDPOINT, MINIO_SECURE)
        _minio_client = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=secure,
            region=MINIO_REGION,
        )
    return _minio_client


def ensure_bucket():
    global _bucket_ready
    if _bucket_ready:
        return
    client = get_minio_client()
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET, location=MINIO_REGION)
    _bucket_ready = True

def compile_latex(latex_source: str):
    # Input size guard
    if len(latex_source.encode("utf-8")) > MAX_LATEX_BYTES:
        return {
            "success": False,
            "log": f"LaTeX source too large. Limit is {MAX_LATEX_BYTES} bytes."
        }

    build_id = str(uuid.uuid4())
    build_dir = BUILD_ROOT / build_id
    build_dir.mkdir(parents=True, exist_ok=True)

    tex_file = build_dir / "main.tex"
    pdf_file = build_dir / "main.pdf"

    tex_file.write_text(latex_source, encoding="utf-8")

    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "main.tex"
    ]

    try:
        process = subprocess.run(
            cmd,
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=LATEX_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(build_dir, ignore_errors=True)
        return {
            "success": False,
            "log": f"pdflatex timed out after {LATEX_TIMEOUT_SECONDS}s"
        }

    log = process.stdout.decode()

    if process.returncode != 0 or not pdf_file.exists():
        return {
            "success": False,
            "log": log
        }

    object_key = f"{build_id}.pdf"

    try:
        ensure_bucket()
        client = get_minio_client()
        with pdf_file.open("rb") as file_obj:
            client.put_object(
                MINIO_BUCKET,
                object_key,
                file_obj,
                pdf_file.stat().st_size,
                content_type="application/pdf",
            )
        presigned_url = client.presigned_get_object(
            MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=PDF_URL_TTL_SECONDS),
        )
    except S3Error as exc:
        return {
            "success": False,
            "log": f"Upload to storage failed: {exc}"
        }
    finally:
        if KEEP_LOCAL_OUTPUT:
            final_pdf = OUTPUT_DIR / object_key
            if pdf_file.exists():
                pdf_file.replace(final_pdf)
        shutil.rmtree(build_dir, ignore_errors=True)

    return {
        "success": True,
        "build_id": build_id,
        "object_key": object_key,
        "presigned_url": presigned_url,
    }
