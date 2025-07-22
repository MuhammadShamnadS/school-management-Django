import re
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from datetime import date, timedelta

def validate_roll_number(value):
    if not re.fullmatch(r'\d{3}', value):
        raise ValidationError("Roll number must be exactly 3 digits.")

def validate_employee_id(value):
    if not re.fullmatch(r'EMP\d+', value):
        raise ValidationError("Employee ID must start with 'EMP' followed by numbers, e.g. EMP100.")

def validate_phone_number(value):
    if not re.fullmatch(r'[1-9]\d{9}', value):
        raise ValidationError("Phone number must be exactly 10 digits and cannot start with 0.")

def validate_name(value):
    if not re.fullmatch(r'^[a-zA-Z ]+$', value):
        raise ValidationError("Name must contain only alphabets.")

def validate_date_of_birth(value):
    today = date.today()
    age_limit = today.replace(year=today.year - 8)
    if value > age_limit:
        raise ValidationError("Date of birth must be at least 8 years before today.")
