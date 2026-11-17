from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=True)
    extracted_text = Column(Text, nullable=False, default="")

    vendor = Column(String(255), nullable=True, index=True)
    document_date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=True, index=True)

    verdict = Column(String(50), nullable=False, default="review", index=True)
    explanation = Column(Text, nullable=False, default="")
    embedding = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    matches = relationship(
        "DocumentMatch",
        foreign_keys="DocumentMatch.document_id",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentMatch(Base):
    __tablename__ = "document_matches"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    matched_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    similarity = Column(Float, nullable=False)
    reason = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="matches",
    )
    matched_document = relationship("Document", foreign_keys=[matched_document_id])
