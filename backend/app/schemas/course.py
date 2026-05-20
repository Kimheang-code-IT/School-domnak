from datetime import datetime

from app.schemas.common import CamelModel


class CourseBase(CamelModel):
    course_name: str
    course_name_km: str | None = None
    description: str | None = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(CamelModel):
    course_name: str | None = None
    course_name_km: str | None = None
    description: str | None = None


class CourseRead(CourseBase):
    id: int
    total_class: int = 0
    created_at: datetime | None = None
