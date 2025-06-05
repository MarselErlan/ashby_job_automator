from sqlalchemy import Column, Integer, Text, JSON, DateTime
from sqlalchemy.sql import func
from src.app.db.session import Base

class ExtractedFields(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    job_url = Column(Text, nullable=False)
    fields = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())