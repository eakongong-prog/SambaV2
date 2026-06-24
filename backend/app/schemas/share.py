from pydantic import BaseModel, Field
from typing import Optional


class ShareCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    comment: str = ""
    path: str = ""
    valid_users: str = ""
    admin_users: str = ""
    writable: str = "yes"
    browseable: str = "yes"
    create_mask: str = "0777"
    directory_mask: str = "0777"


class ShareUpdate(BaseModel):
    comment: Optional[str] = None
    path: Optional[str] = None
    valid_users: Optional[str] = None
    admin_users: Optional[str] = None
    writable: Optional[str] = None
    browseable: Optional[str] = None
    create_mask: Optional[str] = None
    directory_mask: Optional[str] = None
