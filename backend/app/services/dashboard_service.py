from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.class_model import SchoolClass
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice
from app.models.student import Student


def get_summary(db: Session) -> dict:
    revenue = db.scalar(select(func.coalesce(func.sum(Invoice.total), 0))) or 0
    return {
        "totalCategories": db.scalar(select(func.count(Category.id))) or 0,
        "totalCourses": db.scalar(select(func.count(Course.id))) or 0,
        "totalClasses": db.scalar(select(func.count(SchoolClass.id))) or 0,
        "totalStudents": db.scalar(select(func.count(Student.id))) or 0,
        "totalEnrollments": db.scalar(select(func.count(Enrollment.id))) or 0,
        "totalRevenue": revenue,
        "charts": {
            "sales": [],
            "categories": [],
            "courses": [],
        },
    }
