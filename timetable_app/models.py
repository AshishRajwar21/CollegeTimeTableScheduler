from django.db import models
from django.contrib.auth.models import User
import uuid # Import uuid

class College(models.Model):
    college_code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    address = models.TextField()

    def __str__(self):
        return self.name

class Department(models.Model):
    department_code = models.CharField(max_length=10, unique=True)
    college = models.ForeignKey(College, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Classroom(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.room_number} ({self.department.name})"

class Lab(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    lab_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.lab_number} ({self.department.name})"

class Course(models.Model):
    course_code = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Faculty(models.Model):
    FACULTY_ROLES = (
        ('faculty', 'Faculty'),
        ('hod', 'Head of Department'),
        ('dean', 'Dean'),
    )
    faculty_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    expertise_courses = models.ManyToManyField(Course)
    role = models.CharField(max_length=10, choices=FACULTY_ROLES, default='faculty')

    def __str__(self):
        return self.user.username

class Semester(models.Model):
    SEMESTER_CHOICES = (
        (1, '1st'),
        (2, '2nd'),
        (3, '3rd'),
        (4, '4th'),
        (5, '5th'),
        (6, '6th'),
        (7, '7th'),
        (8, '8th'),
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    semester_number = models.IntegerField(choices=SEMESTER_CHOICES) # Changed to choices
    courses = models.ManyToManyField(Course)

    def __str__(self):
        return f"{self.department.name} - Semester {self.get_semester_number_display()}" #display value

class Timetable(models.Model):
    day = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE) # Changed on_delete
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course.name} - {self.day} {self.start_time}-{self.end_time}"
