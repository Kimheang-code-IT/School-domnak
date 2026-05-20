from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.course import Course
from app.repositories.base import BaseRepository
from app.schemas.common import TableQueryParams
from app.schemas.course import CourseRead


class CourseRepository(BaseRepository[Course]):
    def __init__(self) -> None:
        super().__init__(Course)

    def list_courses(self, db: Session, query: TableQueryParams) -> tuple[list[CourseRead], int]:
        total_class = func.count(SchoolClass.id).label("total_class")
        statement = (
            select(Course, total_class)
            .outerjoin(SchoolClass, SchoolClass.course_id == Course.id)
            .group_by(Course.id)
        )
        rows, total = self.list_simple(
            db,
            query,
            base_statement=statement,
            sort_map={
                "id": Course.id,
                "courseName": Course.course_name,
                "courseNameKm": Course.course_name_km,
                "description": Course.description,
                "totalClass": total_class,
                "createdAt": Course.created_at,
            },
            search_columns=[Course.course_name, Course.course_name_km, Course.description],
            date_column=Course.created_at,
        )
        data = [
            CourseRead(
                id=course.id,
                course_name=course.course_name,
                course_name_km=course.course_name_km,
                description=course.description,
                total_class=class_count,
                created_at=course.created_at,
            )
            for course, class_count in rows
        ]
        return data, total
