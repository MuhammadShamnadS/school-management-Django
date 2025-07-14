from rest_framework import serializers
from .models import CustomUser,Teacher,Student,Exam,ExamSubmission,Question,Answer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

class TeacherUserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, data):
        pwd = data.pop("password")
        user = CustomUser(**data)
        user.set_password(pwd)
        user.role = "teacher"
        user.save()
        return user

class StudentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, data):
        pwd = data.pop("password")
        user = CustomUser(**data)
        user.set_password(pwd)
        user.role = "student"
        user.save()
        return user

class TeacherSerializer(serializers.ModelSerializer):
    user = TeacherUserSerializer()

    class Meta:
        model  = Teacher
        fields = "__all__"

    def create(self, data):
        user_data = data.pop("user")
        user      = TeacherUserSerializer().create(user_data)
        return Teacher.objects.create(user=user, **data)

    def update(self, instance, data):
        user_data = data.pop("user", {})
        for f, v in user_data.items():
            setattr(instance.user, f, v)
        instance.user.save()

        for f, v in data.items():
            setattr(instance, f, v)
        instance.save()
        return instance

class StudentSerializer(serializers.ModelSerializer):
    user = StudentUserSerializer()

    class Meta:
        model  = Student
        fields = "__all__"

    def create(self, data):
        user_data = data.pop("user")
        user      = StudentUserSerializer().create(user_data)
        return Student.objects.create(user=user, **data)

    def update(self, instance, data):
        user_data = data.pop("user", {})
        for f, v in user_data.items():
            setattr(instance.user, f, v)
        instance.user.save()

        for f, v in data.items():
            setattr(instance, f, v)
        instance.save()
        return instance
    
class QuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Question
        fields = [
            "id", "exam", "text",
            "option1", "option2", "option3", "option4",
            "correct_option",
        ]
        read_only_fields = ["id"]

class QuestionPublicSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Question
        fields = ["id", "text", "option1", "option2", "option3", "option4"]

class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model  = Exam
        fields = [
            "id", "title", "start_time",
            "duration_minutes", "assigned_teacher",
            "questions",
        ]
        read_only_fields = ["id", "questions"]

class ExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Exam
        fields = ["id", "title", "start_time", "duration_minutes", "assigned_teacher"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        request_user = self.context["request"].user

        if request_user.role == "teacher":
            if not hasattr(request_user, "teacher"):
                raise serializers.ValidationError("Teacher profile missing for this user.")
            attrs["assigned_teacher"] = request_user.teacher
        else:  
            if "assigned_teacher" not in attrs:
                raise serializers.ValidationError({"assigned_teacher": "This field is required."})
        return attrs

    def create(self, attrs):
        user = self.context["request"].user
        exam = Exam.objects.create(created_by=user, **attrs)

        if hasattr(exam, "students"):
            exam.students.set(
                Student.objects.filter(assigned_teacher=attrs["assigned_teacher"])
            )
        return exam
    
class TeacherExamCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Exam
        fields = ["id", "title", "start_time", "duration_minutes"]  
        read_only_fields = ["id"]

    def create(self, attrs):
        user = self.context["request"].user         
        attrs["assigned_teacher"] = user.teacher      
        exam = Exam.objects.create(created_by=user, **attrs)

        if hasattr(exam, "students"):
            exam.students.set(Student.objects.filter(assigned_teacher=user.teacher))
        return exam

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Answer
        fields = ["question", "selected_option"]

class AnswerResultSerializer(serializers.ModelSerializer):
    question_text  = serializers.CharField(source="question.text", read_only=True)
    correct_option = serializers.IntegerField(source="question.correct_option", read_only=True)
    is_correct     = serializers.SerializerMethodField()

    def get_is_correct(self, obj):
        return obj.selected_option == obj.question.correct_option

    class Meta:
        model  = Answer
        fields = [
            "question", "question_text",
            "selected_option", "correct_option",
            "is_correct",
        ]

class ExamSubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, write_only=True)

    class Meta:
        model  = ExamSubmission
        fields = ["id", "exam", "answers", "score"]
        read_only_fields = ["id", "score"]

    def create(self, validated_data):
        request_user = self.context["request"].user
        answers_data = validated_data.pop("answers")

        student = Student.objects.get(user=request_user)

        submission = ExamSubmission.objects.create(student=student, exam=validated_data["exam"], score=0)

        score = 0
        for item in answers_data:
            question = item["question"]
            selected = item["selected_option"]
            Answer.objects.create(
                submission=submission,
                question=question,
                selected_option=selected,
            )
            if selected == question.correct_option:
                score += 1

        submission.score = score
        submission.save()
        return submission

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid    = serializers.CharField()
    token  = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

    def validate(self, attrs):
        try:
            uid  = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = CustomUser.objects.get(pk=uid)
        except (ValueError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid link")

        if not PasswordResetTokenGenerator().check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired token")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user