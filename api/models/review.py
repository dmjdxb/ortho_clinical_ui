"""
Review decision models.

GOVERNANCE:
- Accept requires clinician notes
- Reject REQUIRES replacement ICD-10
"""

from pydantic import BaseModel, Field, field_validator


class AcceptDecision(BaseModel):
    """Decision to accept the suggested ICD-10 code."""

    clinician_id: str = Field(..., min_length=1)
    notes: str = Field(..., min_length=10)


class RejectReplaceDecision(BaseModel):
    """Decision to reject and replace the ICD-10 code."""

    clinician_id: str = Field(..., min_length=1)
    replacement_icd10: str = Field(..., min_length=3)
    reason: str = Field(..., min_length=20)

    @field_validator("replacement_icd10")
    @classmethod
    def validate_icd10_format(cls, v: str) -> str:
        """Basic ICD-10 format validation."""
        v = v.strip().upper()
        # Basic check: ICD-10 codes typically start with a letter
        if not v[0].isalpha():
            raise ValueError("ICD-10 code must start with a letter")
        return v
