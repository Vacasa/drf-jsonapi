from django.urls import path
from rest_framework import views

urlpatterns = [
    path('tests', views.APIView.as_view(), name='tests'),
]
