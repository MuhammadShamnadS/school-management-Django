from django.contrib import admin
from .models import CustomUser
from .models import Teacher, Student

admin.site.register(CustomUser)
admin.site.register(Teacher)
admin.site.register(Student)

