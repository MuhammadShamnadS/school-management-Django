from rest_framework import status
from django.urls import reverse
import pytest
pytestmark = pytest.mark.django_db

def test_admin_can_crud_student(admin_user, auth_client, teacher):
    client = auth_client(admin_user)
    url = reverse("student-list")
    data = {
        "user": {"username":"newstud","email":"s@x.com","first_name":"S","last_name":"T","password":"p"},
        "phone":"1","roll_number":"RX1","student_class":"9‑A",
        "date_of_birth":"2011-01-01","admission_date":"2024-06-01",
        "status":"active","assigned_teacher": teacher.id,
    }
 
    resp = client.post(url, data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    pk = resp.data["id"]
    assert client.get(f"{url}/{pk}").status_code == 200
    assert client.patch(f"{url}/{pk}", {"phone":"999"}).status_code == 200
    assert client.delete(f"{url}/{pk}").status_code == 204
