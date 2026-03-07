from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional
from datetime import datetime

class JobSchema(BaseModel):
    title: str = Field(..., min_length=2, description="Job title")
    company_name: str = Field(..., min_length=1, description="Company providing the job")
    
    # Optional fields but stringified to match dataset expectations
    location: Optional[str] = ""
    experience: Optional[str] = ""
    salary: Optional[str] = ""
    keyskills: Optional[str] = ""
    role: Optional[str] = ""
    industry_type: Optional[str] = ""
    employment_type: Optional[str] = ""
    education: Optional[str] = ""
    posted: Optional[str] = ""
    
    # URL is optional but if present, should be valid
    url: Optional[str] = ""
    
    # Important for scoring but potentially empty
    jobdescription: Optional[str] = ""

    @validator("title", pre=True)
    def title_must_not_be_empty(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Title cannot be empty")
        return str(v).strip()

    @validator("company_name", "keyskills", pre=True)
    def clean_strings(cls, v):
        if not v:
            return ""
        return str(v).strip()
