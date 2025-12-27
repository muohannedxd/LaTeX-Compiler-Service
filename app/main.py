import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from pydantic import BaseModel

from .compiler import compile_latex, ensure_bucket, get_minio_client
from .config import MAX_CONCURRENT_COMPILES, MAX_LATEX_BYTES, MINIO_BUCKET

app = FastAPI(title="LaTeX Compiler Service")


compile_semaphore = asyncio.Semaphore(MAX_CONCURRENT_COMPILES)

class CompileRequest(BaseModel):
    presentation_id: str
    latex: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/compile")
async def compile_endpoint(payload: CompileRequest):
    if len(payload.latex.encode("utf-8")) > MAX_LATEX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"LaTeX source too large. Limit is {MAX_LATEX_BYTES} bytes."
        )

    async with compile_semaphore:
        print(
            "[compile] start",
            "presentation_id",
            payload.presentation_id,
            "payload_bytes",
            len(payload.latex.encode("utf-8")),
        )
        result = await run_in_threadpool(compile_latex, payload.presentation_id, payload.latex)

    if not result["success"]:
        print("[compile] failure", result.get("log", ""))
        raise HTTPException(
            status_code=400,
            detail=result["log"]
        )

    print(
        "[compile] success",
        "build_id",
        result["build_id"],
        "presigned",
        bool(result.get("presigned_url")),
        "overwritten",
        result.get("overwritten", False),
    )
    return {
        "status": "success",
        "build_id": result["build_id"],
        "pdf_url": f"/pdf/{result['build_id']}",
        "presigned_url": result.get("presigned_url"),
        "overwritten": result.get("overwritten", False),
    }

@app.get("/pdf/{build_id}")
async def get_pdf(build_id: str):
    object_key = f"{build_id}.pdf"
    try:
        print("[pdf] fetch", object_key)
        ensure_bucket()
        client = get_minio_client()
        obj = client.get_object(MINIO_BUCKET, object_key)
    except S3Error as exc:
        if exc.code == "NoSuchKey":
            print("[pdf] not_found", object_key)
            raise HTTPException(status_code=404, detail="PDF not found")
        print("[pdf] error", object_key, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    def stream():
        try:
            for chunk in obj.stream(32 * 1024):
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(
        stream(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={build_id}.pdf"
        },
    )
