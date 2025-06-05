from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class ExtractedFieldsBase(BaseModel):
    job_url: str
    fields: Dict[str, Any]

class ExtractedFieldsCreate(ExtractedFieldsBase):
    pass

class ExtractedFields(ExtractedFieldsBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FillFormRequest(BaseModel):
    job_url: str
    fields: Dict[str, Any]