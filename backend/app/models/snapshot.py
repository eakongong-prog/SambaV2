import datetime
from sqlalchemy import Column, Integer, DateTime
from ..database import Base


class SessionSnapshot(Base):
    """Periodic snapshot of active SMB sessions for dashboard charting."""

    __tablename__ = "session_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, nullable=False, index=True)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
