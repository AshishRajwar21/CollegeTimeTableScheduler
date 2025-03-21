from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from .models import College, Department, Classroom, Course, Faculty, Semester, Timetable,Lab
from datetime import time, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory, ModelForm, CheckboxSelectMultiple #Import CheckboxSelectMultiple
from django.contrib import messages
from django.db import models #Import models
import datetime # Import datetime
import random # Import random
import uuid


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Creates a Faculty with a random faculty_id
            faculty_id = str(uuid.uuid4())[:8]  # Generate a random string of 8 characters
            default_department = Department.objects.first()
            if default_department:
                Faculty.objects.create(user=user, department=default_department, faculty_id=faculty_id)
                login(request, user)
                return redirect('timetable_list')
            else:
                messages.error(request, "Please create a department before signing up.")
                return redirect('signup')
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
    user = request.user
    if hasattr(user, 'faculty'): # Check if the user is a faculty
        department = user.faculty.department
        timetables = Timetable.objects.filter(semester__department=department).order_by('day', 'start_time')
        #Personalized Timetable
        return render(request, 'timetable_list.html', {'timetables': timetables, 'user_type': 'faculty', 'faculty_user': user})
    else: #else it is student
        # Assuming a student can be linked to a department and semester.  You might need to adjust this based on your actual model
        student_semester = request.GET.get('semester') # get semester from parameter.
        department = Department.objects.first() # Replace this logic
        if student_semester:
            timetables = Timetable.objects.filter(semester__department=department, semester__semester_number=student_semester).order_by('day', 'start_time')
        else:
             timetables = Timetable.objects.filter(semester__department=department).order_by('day', 'start_time')
        return render(request, 'timetable_list.html', {'timetables': timetables, 'user_type': 'student', 'student_semester':student_semester})

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
        max_classes_per_day = 6
        max_classes_per_week = 3 # Maximum classes per week per course

        Timetable.objects.filter(semester__department=department).delete()

        for semester in semesters:
            courses = list(semester.courses.all()) # Convert to list for shuffling
            for course in courses:
                scheduled_count = 0 #keep track of how many classes are scheduled for this course
                available_days = days[:] # Create a copy of the days list
                random.shuffle(available_days)
                for day in available_days:
                    if scheduled_count >= max_classes_per_week:
                        break
                    classes_today = 0
                    scheduled_courses_today = set()
                    current_time = start_time
                    while current_time < end_time:
                        if classes_today >= max_classes_per_day:
                            break

                        if recess_start <= current_time < recess_end:
                            current_time = recess_end
                            continue
                        end_current_time = (datetime.datetime.combine(datetime.date(1, 1, 1), current_time) + class_duration).time()

                        if end_current_time > end_time:
                            break

                        # Check if the course has already been scheduled today
                        if course in scheduled_courses_today:
                            current_time = end_current_time
                            continue

                        #Find faculty teaching this course in this department
                        faculty = Faculty.objects.filter(expertise_courses=course, department=department).first()
                        if not faculty:
                            messages.error(request, f"No faculty found to teach {course.name} in your department.")
                            current_time = end_current_time
                            continue
                        if Timetable.objects.filter(day=day, start_time=current_time, faculty=faculty).exists():
                            current_time = end_current_time
                            continue

                        #Try to find a classroom in the department.
                        classroom = Classroom.objects.filter(department=department).first()

                        if not classroom:
                            classroom = Classroom.objects.first()

                        if Timetable.objects.filter(day=day, start_time=current_time, classroom=classroom).exists():
                            available_classrooms = Classroom.objects.exclude(id__in=Timetable.objects.filter(day=day, start_time=current_time).values_list('classroom_id', flat=True))
                            if available_classrooms.exists():
                                classroom = available_classrooms.first()
                            else:
                                current_time = end_current_time
                                continue

                        if not classroom:
                            current_time = end_current_time
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
                        scheduled_courses_today.add(course)
                        scheduled_count += 1
                        break # Break after scheduling one course in the current time slot
                    if scheduled_count >= max_classes_per_week:
                        break
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
            return redirect('timetable_list')
        else:
             messages.error(request, 'Error updating courses.')
    else:
        formset = SemesterCourseFormSet(instance=semester)

    return render(request, 'manage_semester_courses.html', {
        'formset': formset,
        'semester': semester,
    })

@login_required
def view_rooms(request):
    department = request.user.faculty.department
    classrooms = Classroom.objects.filter(department=department)
    labs = Lab.objects.filter(department=department)
    today = datetime.date.today().strftime('%A') # Get the day name
    current_time = datetime.datetime.now().time()

    #Get the list of busy rooms.
    busy_classrooms = Timetable.objects.filter(day=today, start_time__lte=current_time, end_time__gte=current_time, classroom__department=department).values_list('classroom', flat=True)
    busy_labs = Timetable.objects.filter(day=today, start_time__lte=current_time, end_time__gte=current_time, classroom__department=department).values_list('classroom', flat=True) # Assuming labs are also using Classroom model


    return render(request, 'view_rooms.html', {
        'classrooms': classrooms,
        'labs': labs,
        'busy_classrooms': busy_classrooms,
        'busy_labs': busy_labs,
        'current_time': current_time,
    })
