"""Database models and session setup for GradeOps.

Using SQLite via SQLAlchemy for zero-config local development and testing.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generator

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Text, Boolean,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="ta")  # 'instructor' | 'ta'
    created_at = Column(DateTime, default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, default="public", index=True)
    title = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rubrics = relationship("Rubric", back_populates="exam", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="exam", cascade="all, delete-orphan")


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    version = Column(String, nullable=False)
    title = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    max_marks = Column(Float, nullable=False)
    course_instructions = Column(Text, default="")
    criteria = Column(JSON, nullable=False)  # List of Criterion dicts
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="rubrics")
    crops = relationship("Crop", back_populates="rubric", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_anon_id = Column(String, nullable=False, index=True)
    source_pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="papers")
    crops = relationship("Crop", back_populates="paper", cascade="all, delete-orphan")


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String, nullable=False)
    rubric_id = Column(Integer, ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String, nullable=False)
    anonymized_path = Column(String, nullable=False)
    bbox = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="crops")
    rubric = relationship("Rubric", back_populates="crops")
    gradings = relationship("Grading", back_populates="crop", cascade="all, delete-orphan")
    aggregate = relationship("GradingAggregate", back_populates="crop", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="crop", cascade="all, delete-orphan")


class Grading(Base):
    __tablename__ = "gradings"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False)
    rubric_id = Column(Integer, ForeignKey("rubrics.id"), nullable=False)
    pass_num = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    per_criterion = Column(JSON, nullable=False)
    justification = Column(Text, default="")
    transcript = Column(Text, default="")
    flags = Column(JSON, default=list)
    critic_passed = Column(Boolean, default=True)
    critic_feedback = Column(Text, nullable=True)
    model_version = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop = relationship("Crop", back_populates="gradings")


class GradingAggregate(Base):
    __tablename__ = "grading_aggregates"

    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), primary_key=True)
    median = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    min_score = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    n_passes = Column(Integer, nullable=False)

    crop = relationship("Crop", back_populates="aggregate")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # 'approve' | 'override' | 'flag'
    ai_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop = relationship("Crop", back_populates="reviews")


class PlagiarismFlag(Base):
    __tablename__ = "plagiarism_flags"

    id = Column(Integer, primary_key=True, index=True)
    crop_a_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False)
    crop_b_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False)
    similarity = Column(Float, nullable=False)
    flagged_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    before_state = Column("before", JSON, nullable=True)
    after_state = Column("after", JSON, nullable=True)
    rubric_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)