from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest
from rest_framework.permissions import IsAuthenticated, BasePermission

from users.models import User as _User
from tasks.models import Task

User: type[_User] = get_user_model()

__all__ = [
	'IsOptionsOrHead',
	'IsObjectOwner',
	'IsProjectManager',
	'IsAssignedToObject',
	'IsNotDeleteMethod',
]

class IsOptionsOrHead(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.method in ('OPTIONS', 'HEAD')


class IsObjectOwner(BasePermission):
	'''
	Пользователь == пользователю из поля `created_by` объекта.
	'''

	def has_object_permission(self, request: HttpRequest, view, obj):
		return obj.created_by == request.user


class IsProjectManager(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.user.role == User.Role.PROJECT_MANAGER


class IsAssignedToObject(BasePermission):
	'''
	Пользователь == пользователю из поля `assigned_to` объекта.
	'''
	def has_object_permission(self, request: HttpRequest, view, obj):
		return (request.user and obj.assigned_to == request.user)

class IsNotDeleteMethod(BasePermission):
	'''
	Метод запроса != DELETE.
	'''

	def has_permission(self, request: HttpRequest, view):
		return request.method.upper() != 'DELETE'
