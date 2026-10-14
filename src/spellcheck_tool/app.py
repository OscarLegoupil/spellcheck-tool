import json
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .engines import Engines
from .models import DocumentError, EngineError, Options
from .pipeline import export, load_document, review

STATIC = Path(__file__).parent / "static"


class Choice(BaseModel):
    id: str
    correction: str = Field(max_length=10000)


class ExportRequest(BaseModel):
    choices: list[Choice] = Field(max_length=20000)


@dataclass
class Job:
    id: str
    name: str
    created: float
    state: str = "queued"
    done: int = 0
    total: int = 0
    location: str = ""
    error: str = ""
    document: object = None
    result: dict | None = None
    findings: list | None = None
    cancel: bool = False


def create_app(token=None, engines=None):
    access_token = token or secrets.token_urlsafe(32)
    engines = engines or Engines()
    jobs = {}
    jobs_lock = threading.Lock()
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="proofreading")

    @asynccontextmanager
    async def lifespan(app):
        yield
        for job in jobs.values():
            job.cancel = True
        pool.shutdown(wait=True, cancel_futures=True)
        engines.close()

    app = FastAPI(title="Spellcheck Tool", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.access_token = access_token
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    def authorised(authorization: str = Header(default="")):
        if not secrets.compare_digest(authorization, "Bearer " + access_token):
            raise HTTPException(401, "Open the application using the link printed by the launcher.")

    def cleanup():
        expired = [
            key
            for key, job in jobs.items()
            if time.monotonic() - job.created > 7200 and job.state not in ("queued", "checking")
        ]
        for key in expired:
            del jobs[key]

    def find_job(job_id):
        with jobs_lock:
            cleanup()
            job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "This review has expired. Upload the document again.")
        return job

    def work(job, data, options):
        def progress(done, total, location):
            if job.cancel:
                raise InterruptedError("Review cancelled.")
            job.done, job.total, job.location = done, total, location

        try:
            if job.cancel:
                raise InterruptedError("Review cancelled.")
            job.state = "checking"
            document = load_document(job.name, data)
            result, findings = review(document, options, engines, progress)
            job.document, job.result, job.findings = document, result, findings
            job.state = "complete"
        except (DocumentError, EngineError, InterruptedError) as exc:
            job.state, job.error = "failed", str(exc)
        except Exception:
            job.state, job.error = (
                "failed",
                "The document could not be processed. Try a smaller review copy or run the diagnostic command.",
            )

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/status", dependencies=[Depends(authorised)])
    def status():
        return {"engines": engines.status(), "version": "1.0.0"}

    @app.post("/api/reviews", dependencies=[Depends(authorised)])
    async def start_review(file: UploadFile = File(...), settings: str = Form("{}")):
        try:
            values = json.loads(settings)
            if not isinstance(values, dict):
                raise ValueError
            options = Options(**values)
            if options.language not in ("fi", "en", "mixed") or options.english not in (
                "en-GB",
                "en-US",
            ):
                raise ValueError
            if not isinstance(options.glossary, list) or not all(
                isinstance(w, str) for w in options.glossary
            ):
                raise ValueError
            if not isinstance(options.terminology, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in options.terminology.items()
            ):
                raise ValueError
            if len(options.glossary) > 10000 or len(options.terminology) > 1000:
                raise ValueError
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid review settings.") from None
        data = await file.read(30 * 1024 * 1024 + 1)
        await file.close()
        if len(data) > 30 * 1024 * 1024:
            raise HTTPException(413, "The maximum document size is 30 MB.")
        name = Path((file.filename or "document").replace("\\", "/")).name
        if Path(name).suffix.lower() not in (".pdf", ".docx"):
            raise HTTPException(400, "Choose a .pdf or .docx document.")
        with jobs_lock:
            cleanup()
            if len(jobs) >= 8:
                raise HTTPException(429, "Remove a previous review before adding more documents.")
            job = Job(secrets.token_hex(16), name, time.monotonic())
            jobs[job.id] = job
        pool.submit(work, job, data, options)
        return {"id": job.id, "filename": job.name}

    @app.get("/api/reviews/{job_id}", dependencies=[Depends(authorised)])
    def get_review(job_id: str):
        j = find_job(job_id)
        return {
            "id": j.id,
            "filename": j.name,
            "state": j.state,
            "done": j.done,
            "total": j.total,
            "location": j.location,
            "error": j.error,
            "result": j.result,
        }

    @app.delete("/api/reviews/{job_id}", dependencies=[Depends(authorised)])
    def delete_review(job_id: str):
        j = find_job(job_id)
        j.cancel = True
        if j.state not in ("queued", "checking"):
            with jobs_lock:
                jobs.pop(job_id, None)
        return {"ok": True}

    @app.post("/api/reviews/{job_id}/export", dependencies=[Depends(authorised)])
    def export_review(job_id: str, body: ExportRequest):
        j = find_job(job_id)
        if j.state != "complete":
            raise HTTPException(409, "The review is not complete.")
        try:
            content = export(j.document, j.findings, [c.model_dump() for c in body.choices])
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        path = Path(j.name)
        name = f"{path.stem}_reviewed{path.suffix.lower()}"
        media = (
            "application/pdf"
            if j.document.kind == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return Response(
            content,
            media_type=media,
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''" + quote(name),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
