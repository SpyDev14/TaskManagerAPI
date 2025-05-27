from django.urls import path, include
from rest_framework.routers import SimpleRouter, DefaultRouter

from tasks import views


api_router = DefaultRouter()
api_router.register('tasks', views.TaskViewSet, basename = 'task')

urlpatterns = [
    path('api/', include(api_router.urls))
]