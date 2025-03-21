from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from .models import College, Department, Classroom, Course, Faculty, Semester, Timetable
from datetime import time, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory, ModelForm, CheckboxSelectMultiple #Import CheckboxSelectMultiple
from django.contrib import messages
from django.db import models #Import models
import datetime # Import datetime


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            #Creates a Faculty with a default department.  This should be changed by the HOD or Dean.
            # Ensure a department exists before creating a faculty
            default_department = Department.objects.first()
            if default_department:
                Faculty.objects.create(user=user, department=default_department, faculty_id = "temp_id") #Add other fields
                login(request, user)
                return redirect('timetable_list')
            else:
                # Handle the case where no departments exist.
                messages.error(request, "Please create a department before signing up.")
                return redirect('signup')  # Or another appropriate page
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('timetable_list')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def timetable_list(request):
    timetables = Timetable.objects.all()
    return render(request, 'timetable_list.html', {'timetables': timetables})

def is_hod(user):
    return user.faculty.role == 'hod'

@login_required
@user_passes_test(is_hod)
def generate_timetable(request):
    if request.method == 'POST':
        department = request.user.faculty.department
        semesters = Semester.objects.filter(department=department)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        start_time = time(9, 0)
        end_time = time(18, 0)
        recess_start = time(13, 10)
        recess_end = time(14, 0)
        class_duration = timedelta(minutes=50)
        max_classes_per_day = 6 # Maximum number of different classes per day

        Timetable.objects.filter(semester__department=department).delete()

        for semester in semesters:
            courses = semester.courses.all()
            for day in days:
                classes_today = 0
                scheduled_courses_today = set() # Keep track of scheduled courses for the day
                current_time = start_time
                while current_time < end_time:
                    if classes_today >= max_classes_per_day:
                        break # Move to the next day if the maximum is reached

                    if recess_start <= current_time < recess_end:
                        current_time = recess_end
                        continue
                    end_current_time = (datetime.datetime.combine(datetime.date(1, 1, 1), current_time) + class_duration).time()

                    if end_current_time > end_time:
                        break

                    # Iterate through courses *for the current semester*
                    for course in courses:
                        # Check if the course has already been scheduled today
                        if course in scheduled_courses_today:
                            continue

                        #Find faculty teaching this course in this department
                        faculty = Faculty.objects.filter(expertise_courses=course, department=department).first()
                        if not faculty:
                            messages.error(request, f"No faculty found to teach {course.name} in your department.")
                            continue  # Continue to the next course
                        if Timetable.objects.filter(day=day, start_time=current_time, faculty=faculty).exists():
                            continue

                        #Try to find a classroom in the department.
                        classroom = Classroom.objects.filter(department=department).first()

                        if not classroom:
                            classroom = Classroom.objects.first() # Fallback to any classroom if none in dept.

                        if Timetable.objects.filter(day=day, start_time=current_time, classroom=classroom).exists():
                             # Try other classrooms.
                            available_classrooms = Classroom.objects.exclude(id__in=Timetable.objects.filter(day=day, start_time=current_time).values_list('classroom_id', flat=True))
                            if available_classrooms.exists():
                                classroom = available_classrooms.first()
                            else:
                                continue # No available classrooms, try next time slot

                        if not classroom:
                            continue

                        Timetable.objects.create(
                            day=day,
                            start_time=current_time,
                            end_time=end_current_time,
                            classroom=classroom,
                            course=course,
                            faculty=faculty,
                            semester=semester
                        )
                        current_time = end_current_time
                        classes_today += 1
                        scheduled_courses_today.add(course) # Mark the course as scheduled for the day
                        break # Break after scheduling one course in the current time slot
                    current_time = end_current_time

        messages.success(request, "Timetable generated successfully!")
        return redirect('timetable_list')
    else:
        return render(request, 'generate_timetable.html')

# Define a formset for managing courses in a semester
class SemesterCourseForm(ModelForm):
    class Meta:
        model = Semester
        fields = ['courses']

    courses = models.ManyToManyField(Course) # Removed widget from here

@login_required
@user_passes_test(is_hod)
def manage_semester_courses(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    SemesterCourseFormSet = inlineformset_factory(Semester, Semester.courses.through, form=SemesterCourseForm, extra=0)

    if request.method == 'POST':
        formset = SemesterCourseFormSet(request.POST, instance=semester)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Courses for the semester updated successfully.')
            return redirect('timetable_list')  # Redirect to the timetable list or appropriate page
        else:
             messages.error(request, 'Error updating courses.')
    else:
        formset = SemesterCourseFormSet(instance=semester)

    return render(request, 'manage_semester_courses.html', {
        'formset': formset,
        'semester': semester,
    })
