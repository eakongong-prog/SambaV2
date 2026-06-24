from pydantic import BaseModel, Field
from typing import Optional, List


class SambaUserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)
    full_name: str = ""
    primary_group: str = "smb_public"
    additional_groups: List[str] = []


class SambaUserUpdate(BaseModel):
    full_name: Optional[str] = None
    primary_group: Optional[str] = None
    additional_groups: Optional[List[str]] = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


class BatchImportRequest(BaseModel):
    users: List[SambaUserCreate]
