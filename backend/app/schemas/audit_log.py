from datetime import datetime

from app.schemas.common import CamelModel


class AuditLogRead(CamelModel):
    id: int
    type_action: str
    username: str
    date: datetime
    description: str
