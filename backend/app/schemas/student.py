from datetime import date, datetime

from app.schemas.common import CamelModel


def format_student_code(student_id: int) -> str:
    return f"DS{student_id:06d}"


class StudentBase(CamelModel):
    image: str | None = None
    name_km: str
    name_en: str
    gender: str | None = None
    birthdate: date | None = None
    phone: str | None = None
    province: str | None = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(CamelModel):
    image: str | None = None
    name_km: str | None = None
    name_en: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    phone: str | None = None
    province: str | None = None


class StudentRead(StudentBase):
    id: int
    student_code: str
    student_id: str
    display_id: str
    total_course: int = 0
    created_at: datetime | None = None
