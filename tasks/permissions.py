from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest
from django.db.models           import Q
from rest_framework.viewsets    import ViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, BasePermission, SAFE_METHODS

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


def get_task_qs_filter_with_permissions(view: ViewSet) -> Q:
	"""
	Возвращает Q-объект, фильтрующий QS в соответствии с правами,
	но без прямой зависимости (логически идентичны, но кодом не связанны,
	должно обновляться вручную при изменении логики прав).
	Возвращает все объекты, к которым у пользователя есть доступ GET.
	"""

	user: _User = view.request.user
	q_filter = Q()

	if (user.is_superuser or user.role == User.Role.PROJECT_MANAGER):
		return q_filter

	# обычные пользователи должны видеть только свои задачи (created_by / assigned_to)
	return Q(created_by = user) | Q(assigned_to = user)


class CommentsUnderTaskPermission(BasePermission):
	# POST, GET (list), OPTIONS, HEAD
	def has_permission(self, request: HttpRequest, view: ViewSet):
		return True
		if IsOptionsOrHead().has_permission(request, view):
			return True
		
		# только авторизованные
		if not IsAuthenticated().has_permission(request, view):
			return False
		
		task_pk: int | None = view.kwargs.get('task_pk', None)
		if task_pk is None:
			return False
		
		task = Task.objects.get(pk = task_pk)

		# выглядит так себе
		from tasks.views  import TaskViewSet
		if TaskViewSet().check_object_permissions(request, task):
			return True
		elif (
			IsAssignedToObject().has_object_permission(request, view, task)
			and
			not IsNotDeleteMethod(request, view)
		):
			return True
		

		return False
	

	def has_object_permission(self, request: HttpRequest, view, obj: Comment):
		# GET (detail), OPTIONS, HEAD
		if IsReadOnly().has_permission(request, view):
			return True

		# PUT, PATCH, DELETE
		if IsObjectOwner().has_object_permission(request, view, obj):
			return True
		
		return False
