from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest
from django.db.models           import Q
from django.shortcuts           import get_object_or_404
from rest_framework.viewsets    import ViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, BasePermission, SAFE_METHODS, OperandHolder
from rest_framework.exceptions  import PermissionDenied

from users.models import User as _User
from tasks.models import Task, Comment

User: type[_User] = get_user_model()


class IsOptionsOrHead(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.method in ('OPTIONS', 'HEAD')\


class IsReadOnly(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.method in SAFE_METHODS


class IsObjectOwner(BasePermission):
	'''
	Пользователь == пользователю из поля `created_by` объекта.
	'''
	def has_permission(self, request, view):
		return True

	def has_object_permission(self, request: HttpRequest, view, obj):
		return obj.created_by == request.user


class IsProjectManager(BasePermission):
	def has_permission(self, request: HttpRequest, view):
		return request.user.role == User.Role.PROJECT_MANAGER\


class IsAssignedToObject(BasePermission):
	'''
	Пользователь == пользователю из поля `assigned_to` объекта.
	'''
	def has_permission(self, request, view):
		return True

	def has_object_permission(self, request: HttpRequest, view, obj):
		return (request.user and obj.assigned_to == request.user)


class IsNotDeleteMethod(BasePermission):
	'''
	Метод запроса != DELETE.
	'''

	def has_permission(self, request: HttpRequest, view):
		return request.method.upper() != 'DELETE'

# вынесено здесь для get_task_qs_filter_with_permissions
TASK_PERMISSION: OperandHolder = (
	IsOptionsOrHead | (
		IsAuthenticated & (
			IsAdminUser   | IsProjectManager |
			IsObjectOwner | (IsAssignedToObject & IsNotDeleteMethod)
		)
	)
)

def get_task_qs_filter_with_permissions(view: ViewSet) -> Q:
	"""
	Возвращает Q-объект, фильтрующий QS в соответствии с правами,
	но без прямой зависимости (логически идентичны, но кодом не связанны,
	должно обновляться вручную при изменении логики прав).
	Возвращает все объекты, к которым у пользователя есть доступ GET.

	Можно было реализовать программно, но это будет неоптимизированно и неэффективно.
	"""

	user: _User = view.request.user
	q_filter = Q()

	if (user.is_superuser or user.role == User.Role.PROJECT_MANAGER):
		return q_filter

	# обычные пользователи должны видеть только свои задачи (created_by / assigned_to)
	return Q(created_by = user) | Q(assigned_to = user)


class CommentsUnderTaskPermission(BasePermission):
	def has_permission(self, request: HttpRequest, view: ViewSet):
		# Эти 2 идут отдельно потому, что эти условия не зависят от задачи, хоть там
		# и проводится такая же проверка.
		if IsOptionsOrHead().has_permission(request, view):
			return True
		
		# только авторизованные
		if not IsAuthenticated().has_permission(request, view):
			return False
		

		task_pk = view.kwargs['task_pk']
		task = get_object_or_404(Task, pk = task_pk)

		# выглядит так себе
		from tasks.views import TaskViewSet
		try:
			TaskViewSet().check_object_permissions(request, task)
			return True
		except PermissionDenied:
			pass

		if (
			IsAssignedToObject().has_object_permission(request, view, task)
			and # это был DELETE
			not IsNotDeleteMethod().has_permission(request, view)
		):
			return True
		
		return False
	

	def has_object_permission(self, request: HttpRequest, view, obj: Comment):
		# READ
		if IsReadOnly().has_permission(request, view):
			return True

		# WRITE
		if IsObjectOwner().has_object_permission(request, view, obj):
			return True
		
		return False
