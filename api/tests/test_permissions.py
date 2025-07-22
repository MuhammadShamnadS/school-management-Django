import pytest
from api.permissions import IsAdmin, IsTeacher, IsStudent

pytestmark = pytest.mark.django_db 

class Dummy:
    pass

def req(user):
    d = Dummy()
    d.user = user
    return d

def test_admin_perm(admin_user):
    assert IsAdmin().has_permission(req(admin_user), None)

def test_teacher_perm(teacher_user):
    assert IsTeacher().has_permission(req(teacher_user), None)

def test_student_perm(student_user):
    assert IsStudent().has_permission(req(student_user), None)
