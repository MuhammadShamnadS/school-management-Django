from django.contrib import admin
from .models import CustomUser
from .models import Teacher, Student, Exam, Question, Answer, ExamSubmission

admin.site.register(CustomUser)
admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(ExamSubmission)
admin.site.register(Answer)

