from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, BasePermission

from users.models import User as _User
from tasks.models import Task

User: type[_User] = get_user_model()


class HasTaskPermission(IsAuthenticated):
	def has_object_permission(self, request: HttpRequest, view, obj: Task):
		return bool (
			obj.created_by  == request.user or
			obj.assigned_to == request.user or
			request.user.role == User.Role.PROJECT_MANAGER or
			request.user.is_staff
		)


class IsOptionsOrHead(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.method in ('OPTIONS', 'HEAD')


class IsObjectOwner(BasePermission):
	'''
	requires `created_by` attribute at object
	'''

	def has_object_permission(self, request: HttpRequest, view, obj):
		if not hasattr(obj, 'created_by'):
			return False

		return obj.created_by == request.user


class IsProjectManager(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.user.role == User.Role.PROJECT_MANAGER


class IsAssignedToObject(BasePermission):
	'''
	пользователь назначин к этому объекту
	requires `assigned_to` attribute at object
	'''
	def has_object_permission(self, request: HttpRequest, view, obj):
		if not hasattr(obj, 'assigned_to'):
			return False

		return (request.user and obj.assigned_to == request.user)
