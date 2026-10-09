from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    vendor = Column(String(255), nullable=True, index=True)
    total = Column(Float, nullable=True)
    date = Column(String(32), nullable=True)
    text = Column(Text, nullable=False, default="")
    embedding = Column(Text, nullable=False, default="[]")
    anomaly_score = Column(Float, nullable=False, default=0.0)
    verdict = Column(String(32), nullable=False, default="review")
    explanation = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    matches = relationship("Match", foreign_keys="Match.document_id", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    related_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    similarity = Column(Float, nullable=False)
    reason = Column(String(255), nullable=False)

    document = relationship("Document", foreign_keys=[document_id])
    related_document = relationship("Document", foreign_keys=[related_document_id])
