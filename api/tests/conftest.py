# api/tests/conftest.py
import csv
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from api.models import CustomUser, Teacher, Student, Exam, Question

pytestmark = pytest.mark.django_db

@pytest.fixture
def user_factory():
    def _create(username, role="admin", password="pass", **extra):
        return CustomUser.objects.create_user(
            username=username,
            password=password,
            role=role,
            **extra,
        )
    return _create

@pytest.fixture
def admin_user(user_factory):
    return user_factory(
        "admin",
        role="admin",
        password="adminpass",
        is_staff=True,
        is_superuser=True,
    )

@pytest.fixture
def teacher_user(user_factory):
    return user_factory(
        "teacher",
        role="teacher",
        password="teachpass",
        first_name="Alan",
        last_name="Turing",
        email="teacher@example.com",
    )

@pytest.fixture
def student_user(user_factory):
    return user_factory(
        "student",
        role="student",
        password="studpass",
        first_name="Ada",
        last_name="Lovelace",
        email="student@example.com", 
    )

@pytest.fixture
def teacher(teacher_user):
    return Teacher.objects.create(
        user=teacher_user,
        phone="1112223333",
        subject_specialization="Math",
        employee_id="EMP001",
        date_of_joining="2020-01-01",
        status="active",
    )

@pytest.fixture
def another_teacher(user_factory):
    other_user = user_factory("teach2", role="teacher", password="x")
    return Teacher.objects.create(
        user=other_user,
        phone="9998887777",
        subject_specialization="Science",
        employee_id="EMP002",
        date_of_joining="2021-01-01",
        status="active",
    )

@pytest.fixture
def student(student_user, teacher):
    return Student.objects.create(
        user=student_user,
        phone="1234567890",
        roll_number="R001",
        student_class="10-A",
        date_of_birth="2010-05-01",
        admission_date="2024-06-01",
        status="active",
        assigned_teacher=teacher,
    )

@pytest.fixture
def exam(teacher_user, teacher):
    return Exam.objects.create(
        title="Algebra Quiz",
        created_by=teacher_user,
        assigned_teacher=teacher,
        start_time=timezone.now() - timedelta(minutes=1),
        duration_minutes=5,
    )

@pytest.fixture
def questions(exam):
    qlist = []
    for i in range(5):
        qlist.append(
            Question.objects.create(
                exam=exam,
                text=f"2 + 2 ? #{i}",
                option1="1",
                option2="2",
                option3="3",
                option4="4",
                correct_option=4,
            )
        )
    return qlist

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client(api_client):
    def _login(user):
        api_client.force_authenticate(user)
        return api_client
    return _login

@pytest.fixture
def token_for():
    from rest_framework_simplejwt.tokens import AccessToken
    def _token(user):
        return f"Bearer {AccessToken.for_user(user)}"
    return _token

@pytest.fixture
def sample_csv(tmp_path):
    header = [
        "username", "email", "first_name", "last_name", "password", "phone",
        "roll_number", "student_class", "date_of_birth", "admission_date",
        "status", "assigned_teacher_id",
    ]
    rows = [
        ["bulk1", "b1@x.com", "B", "One", "pass", "111", "B001", "9-A",
         "2011-01-01", "2024-06-01", "active", ""],
        ["bulk2", "b2@x.com", "B", "Two", "pass", "222", "B002", "9-A",
         "2011-02-01", "2024-06-01", "active", ""],
    ]
    path = tmp_path / "students.csv"
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path
