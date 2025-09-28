from django.urls import path
from . import views

app_name = 'uploads'

urlpatterns = [
    path('', views.upload_page, name='upload_page'),
    path('status/<uuid:session_id>/', views.check_study_status, name='check_study_status'),
]