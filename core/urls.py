from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about-us/', views.about, name='about'),
    path('apps/', views.apps_page, name='apps'),
    path('apps/school-timetable/api/<path:path>', views.timetable_api_proxy, name='timetable_api'),
    path('apps/school-timetable/app/', views.timetable_spa, name='timetable_spa'),
    path('apps/school-timetable/app/<path:rest>', views.timetable_spa, name='timetable_spa_asset'),
    path('apps/<slug:slug>/', views.launch_app, name='launch_app'),
]
