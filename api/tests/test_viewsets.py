import datetime as dt
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from api.models import CustomUser, Teacher, Student

def _make_admin(username="admin"):
    return CustomUser.objects.create_user(username=username, password="pwd", role="admin")


def _make_teacher(username="teach", employee_id="EMP100"):
    user = CustomUser.objects.create_user(
        username=username,
        password="pwd",
        role="teacher",
        first_name="T",
        last_name="L",
    )
    teacher = Teacher.objects.create(
        user=user,
        phone="1111111111",
        subject_specialization="Math",
        employee_id=employee_id,
        date_of_joining=dt.date(2025, 1, 1),
        status="active",
    )
    return teacher


def _make_student(username="stud", roll="S001", teacher=None):
    user = CustomUser.objects.create_user(
        username=username,
        password="pwd",
        role="student",
        first_name="S",
        last_name="L",
    )
    student = Student.objects.create(
        user=user,
        phone="2222222222",
        roll_number=roll,
        student_class="10",
        date_of_birth=dt.date(2010, 1, 1),
        admission_date=dt.date(2024, 1, 1),
        status="active",
        assigned_teacher=teacher,
    )
    return student


class TeacherViewSetTests(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.teacher1 = _make_teacher("teach1", "EMP001")
        self.teacher2 = _make_teacher("teach2", "EMP002")

    
        self.student1 = _make_student("stud1", "R001", self.teacher1)
        self.student2 = _make_student("stud2", "R002", self.teacher1)
        self.student3 = _make_student("stud3", "R003", self.teacher2)


    def test_admin_can_list_all_teachers(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("teacher-list")  
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 2


    def test_teacher_me_endpoint_returns_own_profile(self):
        self.client.force_authenticate(user=self.teacher1.user)
        url = reverse("teacher-me") 
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["employee_id"] == self.teacher1.employee_id

    def test_teacher_my_students_only_their_students(self):
        self.client.force_authenticate(user=self.teacher1.user)
        url = reverse("teacher-my-students") 
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.data.get("results", resp.data)
        roll_numbers = {s["roll_number"] for s in body}
        assert roll_numbers == {"R001", "R002"}

    def test_teacher_cannot_list_all_teachers(self):
        self.client.force_authenticate(user=self.teacher1.user)
        url = reverse("teacher-list")
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

class StudentViewSetTests(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.teacher = _make_teacher("teach_main", "EMP200")
        self.student1 = _make_student("stud1", "S001", self.teacher)
        self.student2 = _make_student("stud2", "S002", self.teacher)

    def test_admin_can_list_all_students(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("student-list")  
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 2


    def test_teacher_sees_only_their_students(self):
        self.client.force_authenticate(user=self.teacher.user)
        url = reverse("student-list")
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.data.get("results", resp.data)
        rolls = {s["roll_number"] for s in body}
        assert rolls == {"S001", "S002"}


    def test_student_me_endpoint_works(self):
        self.client.force_authenticate(user=self.student1.user)
        url = reverse("student-me")  # 
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["roll_number"] == "S001"

    def test_student_cannot_list_students(self):
        self.client.force_authenticate(user=self.student1.user)
        url = reverse("student-list")
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_retrieve_other_student_detail(self):
        self.client.force_authenticate(user=self.student1.user)
        url = reverse("student-detail", args=[self.student2.pk])
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
