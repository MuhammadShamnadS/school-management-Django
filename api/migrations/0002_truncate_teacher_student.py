from django.db import migrations

def truncate_teacher_student(apps, schema_editor):
    CustomUser = apps.get_model("api", "CustomUser")
    Teacher = apps.get_model("api", "Teacher")
    Student = apps.get_model("api", "Student")
    Teacher.objects.all().delete()

    for student in Student.objects.all():
        student.delete()

    CustomUser.objects.filter(role__in=["teacher", "student"]).exclude(
        id__in=Teacher.objects.values_list("user_id", flat=True)
    ).exclude(
        id__in=Student.objects.values_list("user_id", flat=True)
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(truncate_teacher_student),
    ]
