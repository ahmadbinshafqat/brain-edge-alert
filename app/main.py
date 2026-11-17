import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Document, DocumentMatch
from app.services.analyzer import analyze_document
from app.services.embedding import dumps_embedding, loads_embedding
from app.services.extractor import extract_text
from app.services.parser import parse_document

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Edge Alert")
templates = Jinja2Templates(directory="app/templates")

ALLOWED_VERDICTS = {"normal", "review", "unusual"}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db),
    vendor: str = Query("", description="Search vendor names"),
    verdict: str = Query("", description="Filter by verdict"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum document total"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum document total"),
):
    vendor = vendor.strip()
    verdict = verdict.strip().lower()

    if verdict and verdict not in ALLOWED_VERDICTS:
        verdict = ""

    amount_error = None
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        amount_error = "Minimum amount cannot be greater than maximum amount. Showing unbounded amount results."
        min_amount = None
        max_amount = None

    query = db.query(Document)

    if vendor:
        query = query.filter(Document.vendor.ilike(f"%{vendor}%"))
    if verdict:
        query = query.filter(Document.verdict == verdict)
    if min_amount is not None:
        query = query.filter(Document.total_amount.isnot(None), Document.total_amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Document.total_amount.isnot(None), Document.total_amount <= max_amount)

    documents = query.order_by(Document.created_at.desc()).limit(100).all()
    total_count = db.query(func.count(Document.id)).scalar() or 0
    filtered_count = len(documents)
    filters_active = bool(vendor or verdict or min_amount is not None or max_amount is not None)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "documents": documents,
            "total_count": total_count,
            "filtered_count": filtered_count,
            "filters_active": filters_active,
            "filters": {
                "vendor": vendor,
                "verdict": verdict,
                "min_amount": "" if min_amount is None else min_amount,
                "max_amount": "" if max_amount is None else max_amount,
            },
            "amount_error": amount_error,
            "allowed_verdicts": ["normal", "review", "unusual"],
        },
    )


@app.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    original_name = Path(file.filename or "upload").name
    stored_name = f"{uuid4().hex}_{original_name}"
    stored_path = Path(settings.upload_dir) / stored_name

    with stored_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    extracted_text = extract_text(stored_path, file.content_type or "")
    parsed = parse_document(extracted_text)

    past_documents = db.query(Document).order_by(Document.created_at.desc()).all()
    analysis = analyze_document(parsed, extracted_text, past_documents)

    document = Document(
        filename=original_name,
        stored_path=str(stored_path),
        content_type=file.content_type,
        extracted_text=extracted_text,
        vendor=parsed.vendor,
        document_date=parsed.document_date,
        total_amount=parsed.total_amount,
        verdict=analysis.verdict,
        explanation=analysis.explanation,
        embedding=dumps_embedding(analysis.embedding),
    )
    db.add(document)
    db.flush()

    for match in analysis.matches:
        db.add(
            DocumentMatch(
                document_id=document.id,
                matched_document_id=match.document_id,
                similarity=match.similarity,
                reason=match.reason,
            )
        )

    db.commit()
    return RedirectResponse(url=f"/documents/{document.id}", status_code=303)


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(document_id: int, request: Request, db: Session = Depends(get_db)):
    document = (
        db.query(Document)
        .options(joinedload(Document.matches).joinedload(DocumentMatch.matched_document))
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "document": document,
            "embedding_dimensions": len(loads_embedding(document.embedding)),
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
