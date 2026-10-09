from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, Match
from app.services.embedding import cosine_similarity, load_embedding


@dataclass
class AnalysisResult:
    verdict: str
    score: float
    explanation: str


def analyze_document(db: Session, doc: Document) -> AnalysisResult:
    prior_docs = db.query(Document).filter(Document.id != doc.id).all()
    same_vendor = [d for d in prior_docs if _same_vendor(d.vendor, doc.vendor)]
    reasons: list[str] = []
    score = 0.0

    _save_similarity_matches(db, doc, prior_docs)

    if not doc.text or doc.text.lower().startswith(("image ocr unavailable", "pdf text extraction failed")):
        score += 0.45
        reasons.append("Text extraction was incomplete, so this needs manual review.")

    if doc.total is None:
        score += 0.35
        reasons.append("No total amount could be confidently extracted.")

    if same_vendor and doc.total is not None:
        past_totals = [d.total for d in same_vendor if d.total is not None]
        if past_totals:
            avg = sum(past_totals) / len(past_totals)
            if avg > 0 and doc.total > avg * settings.anomaly_high_total_multiplier:
                score += 0.75
                reasons.append(f"Total ${doc.total:.2f} is much higher than the {doc.vendor} average of ${avg:.2f}.")
            else:
                reasons.append(f"Total is close to prior {doc.vendor} documents.")
    elif doc.total is not None and doc.total >= settings.anomaly_new_vendor_threshold:
        score += 0.45
        reasons.append(f"Vendor '{doc.vendor}' is new and amount ${doc.total:.2f} is above the review threshold.")
    elif not same_vendor:
        score += 0.15
        reasons.append(f"Vendor '{doc.vendor}' has not been seen before.")

    best_match = db.query(Match).filter(Match.document_id == doc.id).order_by(Match.similarity.desc()).first()
    if best_match:
        if best_match.similarity >= 0.70:
            score -= 0.20
            reasons.append(f"Very similar to prior document #{best_match.related_document_id}.")
        else:
            reasons.append(f"Closest prior document similarity is {best_match.similarity:.2f}.")
    elif prior_docs:
        score += 0.10
        reasons.append("No similar prior document was found.")

    score = max(0.0, min(1.0, score))
    if score >= 0.65:
        verdict = "unusual"
    elif score >= 0.30:
        verdict = "review"
    else:
        verdict = "normal"

    explanation = " ".join(reasons) if reasons else "Looks consistent with past documents."
    return AnalysisResult(verdict=verdict, score=round(score, 2), explanation=explanation)


def _save_similarity_matches(db: Session, doc: Document, prior_docs: list[Document]) -> None:
    current = load_embedding(doc.embedding)
    matches: list[tuple[Document, float]] = []
    for prior in prior_docs:
        sim = cosine_similarity(current, load_embedding(prior.embedding))
        if sim >= settings.similarity_match_threshold:
            matches.append((prior, sim))
    matches.sort(key=lambda item: item[1], reverse=True)
    for prior, sim in matches[:5]:
        db.add(Match(
            document_id=doc.id,
            related_document_id=prior.id,
            similarity=round(sim, 4),
            reason="Local hashed text embedding similarity",
        ))


def _same_vendor(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()
