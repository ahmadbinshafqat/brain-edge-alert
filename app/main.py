import os
import shutil
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Document, Match
from app.services.analyzer import analyze_document
from app.services.embedding import text_embedding_json
from app.services.extractor import extract_text
from app.services.parser import parse_document_fields

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory="app/templates")
app = FastAPI(title="Edge Alert")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return templates.TemplateResponse("index.html", {"request": request, "documents": documents})


@app.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_name = os.path.basename(file.filename).replace(" ", "_")
    stored_path = Path(settings.upload_dir) / safe_name
    counter = 1
    while stored_path.exists():
        stored_path = Path(settings.upload_dir) / f"{stored_path.stem}_{counter}{stored_path.suffix}"
        counter += 1

    with stored_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    text = extract_text(str(stored_path), file.content_type or "")
    fields = parse_document_fields(text, safe_name)

    doc = Document(
        filename=stored_path.name,
        vendor=fields.vendor,
        total=fields.total,
        date=fields.date,
        text=text,
        embedding=text_embedding_json(text),
        verdict="review",
        anomaly_score=0.0,
        explanation="Pending analysis.",
    )
    db.add(doc)
    db.flush()

    result = analyze_document(db, doc)
    doc.verdict = result.verdict
    doc.anomaly_score = result.score
    doc.explanation = result.explanation
    db.commit()

    return RedirectResponse(url=f"/documents/{doc.id}", status_code=303)


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(document_id: int, request: Request, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    matches = db.query(Match).filter(Match.document_id == document_id).order_by(Match.similarity.desc()).all()
    return templates.TemplateResponse("detail.html", {"request": request, "doc": doc, "matches": matches})


@app.get("/api/documents/{document_id}")
def document_json(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "vendor": doc.vendor,
        "total": doc.total,
        "date": doc.date,
        "verdict": doc.verdict,
        "anomaly_score": doc.anomaly_score,
        "explanation": doc.explanation,
    }
