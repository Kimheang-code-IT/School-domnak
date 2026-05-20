from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.class_model import SchoolClass
from app.models.course import Course
from app.models.level import Level
from app.models.enrollment import Enrollment
from app.repositories.base import BaseRepository
from app.schemas.class_schema import ClassRead
from app.schemas.common import TableQueryParams


class ClassRepository(BaseRepository[SchoolClass]):
    def __init__(self) -> None:
        super().__init__(SchoolClass)

    def list_classes(
        self,
        db: Session,
        query: TableQueryParams,
        *,
        category_id: int | None = None,
    ) -> tuple[list[ClassRead], int]:
        student_count = func.count(Enrollment.id).label("student_count")
        statement = (
            select(
                SchoolClass,
                Category.name.label("category_name"),
                Course.course_name,
                Level.level_name_en,
                Level.level_name_km,
                student_count,
            )
            .outerjoin(Category, Category.id == SchoolClass.category_id)
            .outerjoin(Course, Course.id == SchoolClass.course_id)
            .outerjoin(Level, Level.id == SchoolClass.level_id)
            .outerjoin(
                Enrollment,
                and_(Enrollment.class_id == SchoolClass.id, Enrollment.roster_active.is_(True)),
            )
            .group_by(
                SchoolClass.id,
                Category.name,
                Course.course_name,
                Level.level_name_en,
                Level.level_name_km,
            )
        )
        if category_id:
            statement = statement.where(SchoolClass.category_id == category_id)
        rows, total = self.list_simple(
            db,
            query,
            base_statement=statement,
            sort_map={
                "id": SchoolClass.id,
                "name": SchoolClass.name,
                "category": Category.name,
                "courseName": Course.course_name,
                "teacherName": SchoolClass.teacher_name,
                "level": SchoolClass.level,
                "timeIn": SchoolClass.time_in,
                "fullPrice": SchoolClass.full_price,
                "outPrice": SchoolClass.out_price,
                "status": SchoolClass.status,
                "createdAt": SchoolClass.created_at,
            },
            search_columns=[SchoolClass.name, SchoolClass.teacher_name, Category.name, Course.course_name],
            date_column=SchoolClass.created_at,
        )
        data = []
        for school_class, category_name, course_name, level_name_en, level_name_km, count in rows:
            data.append(
                ClassRead(
                    id=school_class.id,
                    name=school_class.name,
                    image=school_class.image,
                    category_id=school_class.category_id,
                    category=category_name,
                    course_id=school_class.course_id,
                    course_name=course_name,
                    level_id=school_class.level_id,
                    teacher_id=school_class.teacher_id,
                    teacher_name=school_class.teacher_name,
                    level=school_class.level or level_name_en,
                    level_km=school_class.level_km or level_name_km,
                    level_name_en=level_name_en or school_class.level,
                    level_name_km=level_name_km or school_class.level_km,
                    class_duration=school_class.class_duration,
                    days_of_week=school_class.days_of_week or [],
                    time_in=school_class.time_in,
                    time_out=school_class.time_out,
                    time_slot=school_class.time_slot,
                    full_price=school_class.full_price,
                    discount_amount=school_class.discount_amount,
                    out_price=school_class.out_price,
                    teacher_commission=school_class.teacher_commission,
                    teacher_commission_mode=school_class.teacher_commission_mode,
                    teacher_commission_percent=school_class.teacher_commission_percent,
                    status=school_class.status,
                    student_count=count,
                    created_at=school_class.created_at,
                )
            )
        return data, total
