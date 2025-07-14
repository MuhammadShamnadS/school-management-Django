import pytest
from rest_framework.test import APITestCase, APIClient
from api.models import CustomUser, Teacher, Student
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import AccessToken

@pytest.mark.django_db

class StudentViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = self.create_user("admin_stu", "admin")
        self.teacher_user = self.create_user("mentor_stu", "teacher")
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            phone="1111111111",
            subject_specialization="Math",
            employee_id="EMP_STU",
            date_of_joining="2022-01-01",
            status="active",
        )
        self.student_user = self.create_student("stud_main", self.teacher).user
        self.create_student("stud_aux", self.teacher)

        self.base = "/api/students"
        self.me = "/api/students/me"

    def create_user(self, username, role="admin", password="pass"):
        return CustomUser.objects.create_user(
            username=username, password=password, role=role
        )

    def create_student(self, username, teacher):
        user = self.create_user(username, "student")
        return Student.objects.create(
            user=user,
            phone="1234567890",
            roll_number=f"ROLL_{username}",
            student_class="9-A",
            date_of_birth="2010-01-01",
            admission_date="2024-06-01",
            status="active",
            assigned_teacher=teacher
        )

    def token_for(self, user):
        return f"Bearer {AccessToken.for_user(user)}"

    def auth(self, u):
        self.client.credentials(HTTP_AUTHORIZATION=self.token_for(u))

    def test_student_me_only(self):
        self.auth(self.student_user)
        res_me = self.client.get(self.me)
        res_list = self.client.get(self.base)
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_list.status_code, 403)

    def test_teacher_list_allowed(self):
        self.auth(self.teacher_user)
        res = self.client.get(self.base)
        self.assertEqual(res.status_code, 200)

        data = res.data.get("results", res.data)
        self.assertGreater(len(data), 0)
        sid = data[0]["id"]
        detail = self.client.get(f"{self.base}/{sid}")
        self.assertEqual(detail.status_code, 200)

    def test_teacher_cant_create_student(self):
        self.auth(self.teacher_user)
        res = self.client.post(self.base, {}, format="json")
        self.assertEqual(res.status_code, 403)
