from django.contrib import admin
from .models import College, Department, Classroom, Lab, Course, Faculty, Semester, Timetable

admin.site.register(College)
admin.site.register(Department)
admin.site.register(Classroom)
admin.site.register(Lab)
admin.site.register(Course)
admin.site.register(Faculty)
admin.site.register(Semester)
admin.site.register(Timetable)
