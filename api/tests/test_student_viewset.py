from rest_framework.test import APITestCase, APIClient
from api.tests.factories import user, teacher, student, token_for


class StudentViewSetTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = user("admin_stu", "admin")
        self.teacher_obj = teacher("mentor_stu")
        self.teacher_user = self.teacher_obj.user

        self.student_user = student("stud_main", self.teacher_obj).user
        student("stud_aux", self.teacher_obj)   

        self.base = "/api/students"
        self.me = "/api/students/me"


    def auth(self, u):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_for(u)}")

    def test_student_me_only(self):
        self.auth(self.student_user)
        self.assertEqual(self.client.get(self.me).status_code, 200)
        self.assertEqual(self.client.get(self.base).status_code, 403)

    def test_teacher_list_allowed(self):
        self.auth(self.teacher_user)

        res = self.client.get(self.base)
        self.assertEqual(res.status_code, 200)

        data = res.data.get("results", res.data)   
        self.assertGreater(len(data), 0)
        sid = data[0]["id"]
        self.assertEqual(self.client.get(f"{self.base}/{sid}").status_code, 200)

    def test_teacher_cant_create_student(self):
        self.auth(self.teacher_user)
        self.assertEqual(self.client.post(self.base, {}, format="json").status_code, 403)
