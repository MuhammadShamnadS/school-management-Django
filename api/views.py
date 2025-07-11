from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Teacher, Student
from .serializers import TeacherSerializer, StudentSerializer
from .permissions import IsAdmin, IsTeacher, IsStudent, IsSelfOrReadOnly

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return Teacher.objects.all()
        if getattr(user, "role", None) == "teacher":
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()
    def get_permissions(self):
        role = getattr(self.request.user, "role", None)
        if role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if role == "teacher":
            if self.action in ["me", "my_students"]:
                return [permissions.IsAuthenticated(), IsTeacher()]
            raise PermissionDenied("Not allowed.")
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)   

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)  

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)  

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsTeacher])
    def me(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)
        return Response(self.get_serializer(teacher).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="me/students",
        permission_classes=[IsTeacher],
    )
    def my_students(self, request):
        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return Response({"detail": "Teacher profile not found."}, status=404)

        students = Student.objects.filter(assigned_teacher=teacher)
        page = self.paginate_queryset(students)
        if page is not None:
            ser = StudentSerializer(page, many=True)
            return self.get_paginated_response(ser.data)

        ser = StudentSerializer(students, many=True)
        return Response(ser.data)

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
        if role == "teacher":
            if self.action in ["list", "retrieve"]:
                return [permissions.IsAuthenticated(), IsTeacher()]
            raise PermissionDenied("Not allowed.")
        if role == "student":
            if self.action == "me":
                return [permissions.IsAuthenticated(), IsStudent()]
            raise PermissionDenied("Not allowed.")
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsStudent])
    def me(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"detail": "Student profile not found."}, status=404)
        return Response(self.get_serializer(student).data)
