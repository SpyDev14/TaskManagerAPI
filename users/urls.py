from django.urls import path

from users import views


urlpatterns = [
    path('api/register/', views.RegisterView.as_view(), name = 'register'),
	path('api/logout/',   views.LogoutView.as_view(),   name = 'logout'),
    path('api/token/',         views.CookieTokenObtainPairView.as_view(), name = 'token-obtain_pair'),
    path('api/token/refresh/', views.CookieTokenRefreshView.as_view(),    name = 'token-refresh'),
]