from django.urls import path
from .views import LoginView, RegisterView


urlpatterns = [
    path('api/register/', RegisterView.as_view(), name = 'api-register'),
	# path('api/logout/',   ...,                  name = 'api-logout'),
    path('api/login/',    LoginView.as_view(),    name = 'api-login'),
]