from datetime import date
from decimal import Decimal
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.finance import Finance
from app.models.invoice import Invoice, InvoiceLine
from app.models.role import Role
from app.models.student import Student
from app.models.user import User
from app.services.auth_service import ensure_default_admin
from app.services.invoice_service import format_invoice_no


def ensure_default_roles(db) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.name == name).one_or_none()
        if role is None:
            role = Role(name=name, permissions=permissions)
            db.add(role)
            db.flush()
        else:
            role.permissions = permissions
        roles[name] = role
    return roles


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        roles = ensure_default_roles(db)
        if db.query(Category).count() > 0:
            ensure_default_admin(db)
            db.commit()
            print("Default admin and role permissions updated; seed data already exists")
            return

        admin = User(
            name="Admin User",
            email="admin@example.com",
            password_hash=get_password_hash("password123"),
            role_id=roles["Admin"].id,
            commission=Decimal("0"),
        )
        staff = User(
            name="Staff User",
            email="staff@example.com",
            password_hash=get_password_hash("password123"),
            role_id=roles["Staff"].id,
            commission=Decimal("0"),
        )
        teacher = User(
            name="Teacher One",
            email="teacher@example.com",
            password_hash=get_password_hash("password123"),
            role_id=roles["Teacher"].id,
            commission=Decimal("10"),
        )
        db.add_all([admin, staff, teacher])
        db.flush()

        programming = Category(name="Programming", description="Coding and software courses")
        language = Category(name="Languages", description="English and communication courses")
        db.add_all([programming, language])
        db.flush()

        python_course = Course(course_name="Python Basics", course_name_km="Python Basics", description="Beginner Python")
        english_course = Course(course_name="English Foundation", course_name_km="English Foundation", description="Beginner English")
        db.add_all([python_course, english_course])
        db.flush()

        python_class = SchoolClass(
            name="Python A1",
            category_id=programming.id,
            course_id=python_course.id,
            teacher_id=teacher.id,
            teacher_name=teacher.name,
            level="Beginner",
            level_km="Beginner",
            class_duration="3 months",
            days_of_week=["Mon", "Wed", "Fri"],
            time_in="18:00",
            time_out="19:30",
            time_slot="18:00-19:30",
            full_price=Decimal("180"),
            discount_amount=Decimal("20"),
            out_price=Decimal("160"),
        )
        english_class = SchoolClass(
            name="English Morning",
            category_id=language.id,
            course_id=english_course.id,
            teacher_id=teacher.id,
            teacher_name=teacher.name,
            level="Foundation",
            level_km="Foundation",
            class_duration="2 months",
            days_of_week=["Tue", "Thu"],
            time_in="08:00",
            time_out="09:30",
            time_slot="08:00-09:30",
            full_price=Decimal("120"),
            discount_amount=Decimal("10"),
            out_price=Decimal("110"),
        )
        db.add_all([python_class, english_class])
        db.flush()

        student_one = Student(name_km="Student One", name_en="Student One", gender="Male", birthdate=date(2005, 1, 10), phone="010123456", province="Phnom Penh")
        student_two = Student(name_km="Student Two", name_en="Student Two", gender="Female", birthdate=date(2006, 5, 20), phone="011123456", province="Kandal")
        db.add_all([student_one, student_two])
        db.flush()

        enrollment_one = Enrollment(student_id=student_one.id, class_id=python_class.id, start_date=date.today(), end_date=date(2026, 8, 30), total_price=Decimal("180"), discount_price=Decimal("20"), price_after_discount=Decimal("160"), register_date=date.today())
        enrollment_two = Enrollment(student_id=student_two.id, class_id=english_class.id, start_date=date.today(), end_date=date(2026, 7, 30), total_price=Decimal("120"), discount_price=Decimal("10"), price_after_discount=Decimal("110"), register_date=date.today())
        db.add_all([enrollment_one, enrollment_two])
        db.flush()

        invoice = Invoice(invoice_no=format_invoice_no(1), student_id=student_one.id, student_name=student_one.name_en, student_phone=student_one.phone, address="Phnom Penh", seller=admin.name, source="Walk-in", subtotal=Decimal("160"), discount_amount=Decimal("0"), total=Decimal("160"))
        invoice.lines.append(InvoiceLine(class_id=python_class.id, product_name=python_class.name, qty=1, price=Decimal("160"), total=Decimal("160")))
        db.add(invoice)

        db.add_all([
            Finance(class_id=python_class.id, electricity=Decimal("10"), water=Decimal("5"), internet=Decimal("15"), total_commission=Decimal("16"), facebook=Decimal("12"), other=Decimal("3"), amount=Decimal("160"), final_price=Decimal("99"), in_price_for_pos=Decimal("160")),
            Finance(class_id=english_class.id, electricity=Decimal("8"), water=Decimal("4"), internet=Decimal("12"), total_commission=Decimal("11"), facebook=Decimal("5"), other=Decimal("2"), amount=Decimal("110"), final_price=Decimal("68"), in_price_for_pos=Decimal("110")),
            Commission(class_id=python_class.id, class_name=python_class.name, student_name=student_one.name_en, teacher_name=teacher.name, source="Walk-in", amount=Decimal("160"), commission=Decimal("16")),
            Commission(class_id=english_class.id, class_name=english_class.name, student_name=student_two.name_en, teacher_name=teacher.name, source="Facebook", amount=Decimal("110"), commission=Decimal("11")),
            AuditLog(type_action="Create", username="system", description="Seeded sample data"),
        ])
        db.commit()
        print("Seed data created")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
