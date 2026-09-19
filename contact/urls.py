from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('', views.contact, name='contact'),
    path('book-demo/', views.book_demo, name='book_demo'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('enquiries/', views.enquiry_list, name='enquiry_list'),
    path('enquiries/<int:pk>/', views.enquiry_detail, name='enquiry_detail'),
    path('users/', views.manage_users, name='manage_users'),
    path('users/<int:pk>/toggle/', views.toggle_user_active, name='toggle_user'),
]
