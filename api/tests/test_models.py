import datetime as dt
import pytest
from django.db import IntegrityError
from api.models import CustomUser, Teacher, Student

pytestmark = pytest.mark.django_db  # every test hits the DB

def test_custom_user_str_representation():
    user = CustomUser.objects.create_user(
        username="admin_user",
        password="admin123",
        role="admin",
    )
    assert str(user) == "admin_user (admin)"

def _create_teacher(username="teach_tim", employee_id="EMP100"):
    """Tiny helper: returns (user, teacher)."""
    user = CustomUser.objects.create_user(
        username=username,
        password="p@ss",
        role="teacher",
        first_name="Tim",
        last_name="Burton",
    )
    teacher = Teacher.objects.create(
        user=user,
        phone="9876543210",
        subject_specialization="Mathematics",
        employee_id=employee_id,
        date_of_joining=dt.date(2025, 7, 1),
        status="active",
    )
    return user, teacher

def test_teacher_creation_and_str():
    user, teacher = _create_teacher()
    assert teacher.user == user
    expected = f"{user.first_name} {user.last_name} - {teacher.subject_specialization}"
    assert str(teacher) == expected

def test_teacher_employee_id_unique_constraint():
    _create_teacher(employee_id="EMP200")
    with pytest.raises(IntegrityError):
        _create_teacher(username="teach_dup", employee_id="EMP200")

def _create_student(username="stud_sue", roll="S001", teacher=None):
    """Helper that returns (user, student)."""
    user = CustomUser.objects.create_user(
        username=username,
        password="pwd",
        role="student",
        first_name="Sue",
        last_name="Storm",
    )
    student = Student.objects.create(
        user=user,
        phone="9123456780",
        roll_number=roll,
        student_class="10",
        date_of_birth=dt.date(2010, 5, 3),
        admission_date=dt.date(2024, 4, 1),
        status="active",
        assigned_teacher=teacher,
    )
    return user, student

def test_student_creation_and_str():
    teacher_user, teacher = _create_teacher(username="teach_alex", employee_id="EMP300")
    user, student = _create_student(teacher=teacher)
    expected = f"{user.first_name} {user.last_name} - {student.roll_number}"
    assert str(student) == expected
    assert student.assigned_teacher == teacher

def test_student_delete_cascades_to_customuser():
    user, student = _create_student()
    student_pk = student.pk
    user_pk = user.pk
    student.delete()
    assert Student.objects.filter(pk=student_pk).count() == 0
    assert CustomUser.objects.filter(pk=user_pk).count() == 0

def test_student_roll_number_unique_constraint():
    _create_student(roll="S999")
    with pytest.raises(IntegrityError):
        _create_student(username="stud_dup", roll="S999")

def test_student_default_ordering_is_by_id():
    _, s2 = _create_student(username="stud2", roll="S102")
    _, s1 = _create_student(username="stud1", roll="S101")
    _, s3 = _create_student(username="stud3", roll="S103")

    ids = list(Student.objects.values_list("id", flat=True))
    assert ids == sorted(ids), "Student queryset is not ordered by id as defined in Meta.ordering"
