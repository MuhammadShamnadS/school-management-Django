import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Teacher, Student
from .serializers import TeacherSerializer, StudentSerializer
from .permissions import IsAdmin, IsTeacher, IsStudent

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["me", "my_students"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        raise PermissionDenied("Not allowed.")

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return Teacher.objects.all()
        if getattr(user, "role", None) == "teacher":
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsTeacher])
    def me(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)
        return Response(self.get_serializer(teacher).data)

    @action(detail=False, methods=["get"], url_path="me/students", permission_classes=[IsTeacher])
    def my_students(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)

        students = Student.objects.filter(assigned_teacher=teacher).order_by("id")
        page = self.paginate_queryset(students)
        if page is not None:
            return self.get_paginated_response(StudentSerializer(page, many=True).data)
        return Response(StudentSerializer(students, many=True).data)
    
    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        teachers = self.get_queryset()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="teachers.csv"'

        writer = csv.writer(response)
        writer.writerow(
            ["Username", "Email", "Phone", "Subject", "Employee ID", "Status"]
        )

        for t in teachers:
            writer.writerow(
                [
                    t.user.username,
                    t.user.email,
                    t.phone,
                    t.subject_specialization,
                    t.employee_id,
                    t.status,
                ]
            )
        return response
    
class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, "role", None)
        if role == "admin":
            return Student.objects.all()
        if role == "teacher":
            return Student.objects.filter(assigned_teacher__user=user)
        if role == "student":
            return Student.objects.filter(user=user)
        return Student.objects.none()

    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher" and self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        if role == "student" and self.action == "me":
            return [permissions.IsAuthenticated(), IsStudent()]
        raise PermissionDenied("Not allowed.")

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsStudent])
    def me(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"detail": "Student profile not found."}, status=404)
        return Response(self.get_serializer(student).data)
    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdmin])
    def export_csv(self, request):
        students = self.get_queryset()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="students.csv"'

        writer = csv.writer(response)
        writer.writerow(
            ["Username", "Email", "Phone", "Assigned Teacher", "Status"]
        )

        for s in students:
            writer.writerow(
                [
                    s.user.username,
                    s.user.email,
                    s.phone,
                    s.assigned_teacher.user.username if s.assigned_teacher else "",
                    s.status,
                ]
            )
        return response