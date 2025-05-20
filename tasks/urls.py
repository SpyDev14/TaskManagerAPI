from django.urls import path, include
from rest_framework.routers import SimpleRouter

api_router = SimpleRouter()


urlpatterns = [
    path('api/', include(api_router.urls))
]