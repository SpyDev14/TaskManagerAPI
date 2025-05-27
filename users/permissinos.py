from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest

from users.models import User as _User # для аннотации
User: type[_User] = get_user_model()


class IsAnonymousOrReadOnly(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.user.is_anonymous or request.method in SAFE_METHODS
