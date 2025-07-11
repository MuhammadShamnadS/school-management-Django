import pytest
from django.contrib.auth.hashers import check_password
from api.serializers import UserSerializer, TeacherSerializer, StudentSerializer
from api.models import CustomUser, Teacher, Student

pytestmark = pytest.mark.django_db  

def test_user_serializer_creates_teacher_user():
    data = {
        "username": "teach_jane",
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "password": "s3cret!",
    }

    serializer = UserSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)

    user = serializer.save()
    assert isinstance(user, CustomUser)
    assert user.role == "teacher"
    assert check_password("s3cret!", user.password)
    assert "password" not in serializer.data  # write‑only

def test_teacher_serializer_creates_user_and_teacher():
    payload = {
        "user": {
            "username": "teach_sam",
            "email": "sam@example.com",
            "first_name": "Sam",
            "last_name": "Lee",
            "password": "p@ssw0rd",
        },
        "employee_id": "EMP001",
        "phone": "9876543210",
        "subject_specialization": "Mathematics",
        "date_of_joining": "2025-07-01",
        "status": "active",
    }

    serializer = TeacherSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True)

    teacher = serializer.save()
    assert Teacher.objects.count() == 1
    assert CustomUser.objects.count() == 1
    assert teacher.user.username == "teach_sam"
    assert teacher.subject_specialization == "Mathematics"
    assert teacher.status == "active"


def test_teacher_serializer_updates_nested_user_and_teacher():
    user = CustomUser.objects.create_user(
        username="teach_joe",
        email="joe@ex.com",
        password="oldpwd",
        role="teacher",
    )
    teacher = Teacher.objects.create(
        user=user,
        employee_id="EMP002",
        phone="9000011111",
        subject_specialization="Physics",
        date_of_joining="2025-05-15",
        status="active",
    )
    update_payload = {
        "user": {"first_name": "Joseph", "last_name": "King"},
        "subject_specialization": "Astro‑Physics",
    }

    serializer = TeacherSerializer(instance=teacher, data=update_payload, partial=True)
    assert serializer.is_valid(raise_exception=True)

    updated = serializer.save()
    updated.refresh_from_db()
    assert updated.subject_specialization == "Astro‑Physics"
    assert updated.user.first_name == "Joseph"
    assert updated.user.last_name == "King"

def test_student_serializer_creates_user_and_student():
    payload = {
        "user": {
            "username": "stud_amy",
            "email": "amy@example.com",
            "first_name": "Amy",
            "last_name": "Brown",
            "password": "stud_pwd",
        },
        "roll_number": "S101",
        "phone": "9123456780",
        "student_class": "10",
        "date_of_birth": "2010-02-15",
        "admission_date": "2024-04-01",
        "status": "active",
    }

    serializer = StudentSerializer(data=payload)
    assert serializer.is_valid(raise_exception=True)

    student = serializer.save()
    assert Student.objects.count() == 1
    assert CustomUser.objects.count() == 1
    assert student.user.role == "student"
    assert student.student_class == "10"


def test_student_serializer_updates_nested_user_and_student():
    user = CustomUser.objects.create_user(
        username="stud_jim",
        email="jim@ex.com",
        password="xyz",
        role="student",
    )
    student = Student.objects.create(
        user=user,
        roll_number="S102",
        phone="9000022222",
        student_class="9",
        date_of_birth="2010-03-20",
        admission_date="2024-04-01",
        status="active",
    )

    update_payload = {
        "user": {"email": "jim_new@ex.com"},
        "student_class": "10",
    }

    serializer = StudentSerializer(instance=student, data=update_payload, partial=True)
    assert serializer.is_valid(raise_exception=True)

    updated = serializer.save()
    updated.refresh_from_db()
    assert updated.student_class == "10"
    assert updated.user.email == "jim_new@ex.com"