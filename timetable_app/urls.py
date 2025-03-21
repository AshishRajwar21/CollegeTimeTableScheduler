from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('timetable/', views.timetable_list, name='timetable_list'),
    path('generate_timetable/', views.generate_timetable, name='generate_timetable'),
    path('semester/<int:semester_id>/courses/', views.manage_semester_courses, name='manage_semester_courses'),
]
