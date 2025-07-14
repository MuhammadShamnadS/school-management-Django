import pytest
from django.db import IntegrityError
from api.models import ExamSubmission, Answer, CustomUser, Teacher, Student, Exam, Question

pytestmark = pytest.mark.django_db

def test_model_strs(admin_user, teacher, student, exam, questions):
    assert str(admin_user) == "admin (admin)"
    assert "Turing" in str(teacher)
    assert "R001" in str(student)
    assert "Algebra" in str(exam)
    assert "2 + 2 ?" in str(questions[0]) 

def test_student_delete_cascades_user(student):
    uid = student.user.id
    student.delete()
    assert not CustomUser.objects.filter(pk=uid).exists()

def test_unique_submission_constraint(student, exam):
    ExamSubmission.objects.create(student=student, exam=exam, score=2)
    with pytest.raises(IntegrityError):
        ExamSubmission.objects.create(student=student, exam=exam, score=3)

def test_answer_belongs_to_submission(student, exam, questions):
    sub = ExamSubmission.objects.create(student=student, exam=exam, score=0)
    ans = Answer.objects.create(
        submission=sub,
        question=questions[0],
        selected_option=4,
    )
    assert ans.submission == sub
    assert ans.question == questions[0]
