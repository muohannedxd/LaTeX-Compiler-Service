# LaTeX Compiler Service

FastAPI service that compiles LaTeX (Beamer) to PDF, uploads to MinIO (S3-compatible), and serves PDFs via streaming or presigned URLs.

## Quick start (Docker Compose)

```bash
docker compose up --build
```

Services:
- API: http://localhost:8010
- MinIO API: http://localhost:9100
- MinIO Console: http://localhost:9101 (login: minio / minio123)

## Environment (defaults in docker-compose.yml)
- Copy `.env.example` to `.env` and adjust if needed.
- Key vars (defaults in .env.example):
  - MINIO_ENDPOINT (compose: http://minio:9000, local: http://127.0.0.1:9100)
  - MINIO_ACCESS_KEY / MINIO_SECRET_KEY (default minio / minio123)
  - MINIO_BUCKET (default latex-builds)
  - MINIO_SECURE (default false)
  - LATEX_TIMEOUT_SECONDS (default 30)
  - MAX_CONCURRENT_COMPILES (default 4)
  - MAX_LATEX_BYTES (default 1000000)

## Test with curl

Compile:
```bash
python3 - <<'PY' | curl -s -X POST -H "Content-Type: application/json" --data-binary @- http://localhost:8010/compile
import json
latex = r"""\documentclass{beamer}
\usetheme{Madrid}
	itle{Test Presentation}
\author{Base44}
\date{\today}

\begin{document}

\begin{frame}
  	itlepage
\end{frame}

\begin{frame}{Second Slide}
  \begin{itemize}
    \item First point
    \item Second point
  \end{itemize}
\end{frame}

\end{document}"""
print(json.dumps({"latex": latex}))
PY
```

You will get `{ "status": "success", "build_id": "...", "pdf_url": "/pdf/<id>", "presigned_url": "..." }`.

Download via the service proxy:
```bash
curl -s http://localhost:8010/pdf/<id> --output my-presentation.pdf
```

Or directly with the presigned URL:
```bash
curl -s "<presigned_url>" --output my-presentation.pdf
```

## Check your PDF in MinIO
1) Open http://localhost:9101
2) Login with `minio` / `minio123`
3) Bucket `latex-builds` will contain `<build_id>.pdf`

## Notes
- PDFs are streamed from MinIO; local temp builds are cleaned after upload.
- Size limit and concurrency guard are configurable via env vars.
