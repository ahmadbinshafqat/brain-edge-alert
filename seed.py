from app.database import Base, engine, SessionLocal
from app.models import Document
from app.services.analyzer import analyze_document
from app.services.embedding import text_embedding_json

SEED_DOCS = [
    {
        "filename": "seed_acme_internet_jan.txt",
        "vendor": "Acme Internet",
        "total": 59.99,
        "date": "2025-01-10",
        "text": "Acme Internet Monthly Bill Date 2025-01-10 Total Due $59.99 Fiber internet service for January",
    },
    {
        "filename": "seed_acme_internet_feb.txt",
        "vendor": "Acme Internet",
        "total": 61.25,
        "date": "2025-02-10",
        "text": "Acme Internet Monthly Bill Date 2025-02-10 Total Due $61.25 Fiber internet service for February",
    },
    {
        "filename": "seed_office_mart.txt",
        "vendor": "Office Mart",
        "total": 34.40,
        "date": "2025-02-15",
        "text": "Office Mart Receipt 2025-02-15 Printer paper pens notebooks Total $34.40",
    },
    {
        "filename": "seed_cloudbox.txt",
        "vendor": "CloudBox Storage",
        "total": 12.00,
        "date": "2025-02-01",
        "text": "CloudBox Storage Invoice Date 2025-02-01 Monthly storage subscription Total USD 12.00",
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Document).count() > 0:
            print("Database already has documents; seed skipped.")
            return
        for item in SEED_DOCS:
            doc = Document(
                filename=item["filename"],
                vendor=item["vendor"],
                total=item["total"],
                date=item["date"],
                text=item["text"],
                embedding=text_embedding_json(item["text"]),
                anomaly_score=0.0,
                verdict="seed",
                explanation="Seed baseline document.",
            )
            db.add(doc)
            db.flush()
            result = analyze_document(db, doc)
            doc.anomaly_score = result.score
            doc.verdict = result.verdict
            doc.explanation = result.explanation
        db.commit()
        print(f"Seeded {len(SEED_DOCS)} documents.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
