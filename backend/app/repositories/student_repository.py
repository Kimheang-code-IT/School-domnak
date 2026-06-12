import re

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.repositories.base import BaseRepository
from app.schemas.common import TableQueryParams
from app.schemas.student import StudentRead, format_student_code
from app.utils.filters import apply_date_filter
from app.utils.pagination import apply_pagination
from app.utils.sorting import apply_sorting


class StudentRepository(BaseRepository[Student]):
    def __init__(self) -> None:
        super().__init__(Student)

    def list_students(
        self,
        db: Session,
        query: TableQueryParams,
        *,
        provinces: list[str] | None = None,
        genders: list[str] | None = None,
        class_ids: list[int] | None = None,
        course_ids: list[int] | None = None,
    ) -> tuple[list[StudentRead], int]:
        total_course = func.count(Enrollment.id).label("total_course")
        statement = (
            select(Student, total_course)
            .outerjoin(Enrollment, Enrollment.student_id == Student.id)
            .group_by(Student.id)
        )

        if query.search:
            search = query.search.strip()
            pattern = f"%{search}%"
            conditions = [
                Student.name_km.ilike(pattern),
                Student.name_en.ilike(pattern),
                Student.phone.ilike(pattern),
                Student.province.ilike(pattern),
                cast(Student.id, String).ilike(pattern),
            ]
            code_match = re.fullmatch(r"DS0*(\d+)", search.upper())
            if code_match:
                conditions.append(Student.id == int(code_match.group(1)))
            statement = statement.where(or_(*conditions))

        if provinces:
            statement = statement.where(Student.province.in_(provinces))

        if genders:
            gender_values: list[str] = []
            for raw in genders:
                normalized = raw.strip().lower()
                if normalized in {"male", "m"}:
                    gender_values.extend(["male", "Male", "m", "M"])
                elif normalized in {"female", "f"}:
                    gender_values.extend(["female", "Female", "f", "F"])
                elif raw.strip():
                    gender_values.append(raw.strip())
            if gender_values:
                statement = statement.where(Student.gender.in_(gender_values))

        if class_ids:
            enrolled_in_class = (
                select(Enrollment.student_id)
                .where(Enrollment.class_id.in_(class_ids))
                .distinct()
            )
            statement = statement.where(Student.id.in_(enrolled_in_class))

        if course_ids:
            enrolled_in_course = (
                select(Enrollment.student_id)
                .join(SchoolClass, SchoolClass.id == Enrollment.class_id)
                .where(SchoolClass.course_id.in_(course_ids))
                .distinct()
            )
            statement = statement.where(Student.id.in_(enrolled_in_course))

        statement = apply_date_filter(statement, Student.created_at, query.date_from, query.date_to)
        total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
        statement = apply_sorting(
            statement,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            sort_map={
                "id": Student.id,
                "studentCode": Student.id,
                "studentId": Student.id,
                "displayId": Student.id,
                "nameKm": Student.name_km,
                "nameEn": Student.name_en,
                "gender": Student.gender,
                "birthdate": Student.birthdate,
                "phone": Student.phone,
                "province": Student.province,
                "totalCourse": total_course,
                "createdAt": Student.created_at,
            },
            default_sort="createdAt",
        )
        rows = db.execute(apply_pagination(statement, query.page, query.limit)).all()
        data = []
        for student, course_count in rows:
            code = format_student_code(student.id)
            data.append(
                StudentRead(
                    id=student.id,
                    student_code=code,
                    student_id=code,
                    display_id=code,
                    image=student.image,
                    name_km=student.name_km,
                    name_en=student.name_en,
                    gender=student.gender,
                    birthdate=student.birthdate,
                    phone=student.phone,
                    province=student.province,
                    total_course=course_count,
                    created_at=student.created_at,
                )
            )
        return data, total
