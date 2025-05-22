from rest_framework.routers import DefaultRouter
from django.urls import path, include

from users import views

api_router = DefaultRouter()


urlpatterns = [
	path('api/', include([
    	path('register/', views.RegisterView.as_view(), name = 'register'),
		path('logout/',   views.LogoutView.as_view(),   name = 'logout'),
    	path('token/',         views.CookieTokenObtainPairView.as_view(), name = 'token-obtain_pair'),
    	path('token/refresh/', views.CookieTokenRefreshView.as_view(),    name = 'token-refresh'),
	]))
]
