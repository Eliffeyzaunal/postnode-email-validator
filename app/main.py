import csv
import io
from functools import lru_cache

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app import __version__
from app.config import get_settings
from app.blocklist.models import (
    BlocklistCheckRequest,
    BlocklistHistoryReport,
    BlocklistNotification,
    BlocklistRunResponse,
    MonitorHealth,
)
from app.blocklist.repository import BlocklistRepository
from app.blocklist.scheduler import BlocklistScheduler
from app.blocklist.service import BlocklistMonitorService
from app.models import (
    BatchMetadataResponse,
    BatchRequest,
    BatchResponse,
    EmailRequest,
    ResultResponse,
    SummaryResponse,
)
from app.parser import InputError, parse_bytes
from app.privacy import email_hash, mask_email
from app.reason_codes import REASON_DESCRIPTIONS
from app.repository import Repository
from app.validator import EmailValidatorService


app = FastAPI(
    title="Postnode E-posta Güvenliği Servisleri",
    version=__version__,
    description=(
        "Liste hijyeni/adres doğrulama ile belirleyici veya seçilebilir canlı DNS "
        "üzerinden periyodik kara liste izleme servislerini sunar."
    ),
)


@lru_cache
def get_service() -> EmailValidatorService:
    settings = get_settings()
    return EmailValidatorService(settings, Repository(settings.database_url))


@lru_cache
def get_blocklist_service() -> BlocklistMonitorService:
    settings = get_settings()
    return BlocklistMonitorService(
        settings,
        BlocklistRepository(settings.database_url),
    )


@lru_cache
def get_blocklist_scheduler() -> BlocklistScheduler:
    return BlocklistScheduler(get_blocklist_service())


def _response_item(item) -> ResultResponse:
    source = item.normalized or item.original
    return ResultResponse(
        row_number=item.row_number,
        masked_email=mask_email(source),
        email_hash=email_hash(source),
        domain=item.domain,
        status=item.status,
        reason_codes=item.reason_codes,
        suggestion=mask_email(item.suggestion) if item.suggestion else None,
    )


def _batch_response(batch_id: str, summary: dict, results: list, filename: str | None = None) -> BatchResponse:
    return BatchResponse(
        batch_id=batch_id,
        filename=filename,
        summary=SummaryResponse(**summary),
        results=[_response_item(item) for item in results],
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/reason-codes", tags=["validation"])
def reason_codes() -> dict[str, str]:
    return {code.value: description for code, description in REASON_DESCRIPTIONS.items()}


@app.get("/api/v1/blocklists/providers", tags=["blocklist"])
def blocklist_providers() -> list[dict]:
    """Etkin sağlayıcıları ve SORBS erişilebilirlik durumunu döndürür."""
    return get_blocklist_service().provider_status()


@app.post(
    "/api/v1/blocklists/check",
    response_model=BlocklistRunResponse,
    tags=["blocklist"],
)
def check_blocklists(
    request: BlocklistCheckRequest | None = None,
) -> BlocklistRunResponse:
    """Bir defalık kontrol yapar; boş gövde örnek varlıkları kullanır."""
    try:
        return get_blocklist_service().run_once(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/blocklists/runs/{run_id}", tags=["blocklist-history"])
def get_blocklist_run(run_id: str) -> dict:
    run = get_blocklist_service().repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Kara liste kontrol kaydı bulunamadı.")
    return run


@app.get(
    "/api/v1/blocklists/runs/{run_id}/notifications",
    response_model=list[BlocklistNotification],
    tags=["blocklist-history"],
)
def get_blocklist_notifications(run_id: str) -> list[dict]:
    if not get_blocklist_service().repository.get_run(run_id):
        raise HTTPException(status_code=404, detail="Kara liste kontrol kaydı bulunamadı.")
    return get_blocklist_service().repository.get_notifications(run_id)


@app.get(
    "/api/v1/blocklists/monitor/status",
    response_model=MonitorHealth,
    tags=["blocklist-monitor"],
)
def get_blocklist_monitor_status() -> MonitorHealth:
    return get_blocklist_scheduler().status()


@app.get(
    "/api/v1/blocklists/reports/history",
    response_model=BlocklistHistoryReport,
    tags=["blocklist-history"],
)
def get_blocklist_history_report(
    days: int = Query(30, ge=1, le=90),
) -> BlocklistHistoryReport:
    try:
        return get_blocklist_scheduler().history_report(days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/validate", response_model=BatchResponse, tags=["validation"])
def validate_email(request: EmailRequest) -> BatchResponse:
    batch_id, summary, item = get_service().validate_one(request.email)
    return _batch_response(batch_id, summary, [item])


@app.post("/api/v1/validate/batch", response_model=BatchResponse, tags=["validation"])
def validate_batch(request: BatchRequest) -> BatchResponse:
    try:
        batch_id, summary, results = get_service().validate_many(request.emails)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _batch_response(batch_id, summary, results)


@app.post("/api/v1/validate/file", response_model=BatchResponse, tags=["validation"])
async def validate_file(file: UploadFile = File(...)) -> BatchResponse:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Dosya boyutu sınırı aşıldı.")
    try:
        emails = parse_bytes(content, file.filename or "upload.csv", settings.max_batch_size)
    except InputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    batch_id, summary, results = get_service().validate_many(emails, filename=file.filename)
    return _batch_response(batch_id, summary, results, file.filename)


@app.get("/api/v1/batches/{batch_id}", response_model=BatchMetadataResponse, tags=["history"])
def get_batch(batch_id: str) -> BatchMetadataResponse:
    batch = get_service().repository.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return BatchMetadataResponse(**batch)


@app.get("/api/v1/batches/{batch_id}/results", response_model=list[ResultResponse], tags=["history"])
def get_batch_results(
    batch_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[ResultResponse]:
    if not get_service().repository.get_batch(batch_id):
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    rows = get_service().repository.get_results(batch_id, offset, limit)
    return [ResultResponse(**row) for row in rows]


@app.get("/api/v1/batches/{batch_id}/export", tags=["history"])
def export_batch(batch_id: str) -> StreamingResponse:
    batch = get_service().repository.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    rows = get_service().repository.get_results(batch_id, 0, get_settings().max_batch_size)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row_number", "masked_email", "email_hash", "domain", "status", "reason_codes", "suggestion"])
    for row in rows:
        writer.writerow([
            row["row_number"], row["masked_email"], row["email_hash"], row["domain"],
            row["status"], "|".join(row["reason_codes"]), row["suggestion"] or ""
        ])
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{batch_id}.csv"'},
    )
