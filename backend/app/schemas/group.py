from pydantic import BaseModel, Field
from typing import List


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)


class UpdateMembersRequest(BaseModel):
    members: List[str] = []
