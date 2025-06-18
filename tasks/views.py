from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth           import get_user_model
from django.db.models              import Q, QuerySet
from rest_framework.permissions    import IsAdminUser, IsAuthenticated
from rest_framework.viewsets       import ModelViewSet
from rest_framework.filters        import SearchFilter, OrderingFilter
from rest_framework                import generics

from users.models      import User as _User
from tasks.permissions import *
from tasks.serializers import FIELDS_FOR_USER_INFO_SERIALIZER
from tasks.serializers import *
from tasks.filters     import TaskOrderingFilter
from tasks.models      import *

User: type[_User] = get_user_model()


class TaskViewSet(ModelViewSet):
	# базовый QS, в get_queryset() есть дополнительная логика
	queryset = Task.objects.order_by('created_at').select_related('created_by', 'assigned_to')
	# для detail нужен .prefetch_related('comments'), но ТОЛЬКО при detail

	serializer_class = TaskSerializer
	permission_classes = [
		IsAuthenticated & (
			IsOptionsOrHead |
			IsObjectOwner |
			(IsAssignedToObject & IsNotDeleteMethod) |
			IsProjectManager |
			IsAdminUser
		)
	]
	filter_backends  = [DjangoFilterBackend, SearchFilter, TaskOrderingFilter]
	filterset_fields = ['priority', 'assigned_to', 'is_completed']
	search_fields    = ['title', 'description']
	ordering_fields  = ['due_date', 'created_at']
	ordering = []


	# Небольшое нарушение solid, так как за права ролей отвечает метод получения qs.
	# Вызывает ошибку 404 вместо 403 при обращении к чужой задаче. С точки зрения 
	# безопасности так даже лучше.
	def get_queryset(self):
		user: _User = self.request.user
		base_qs = super().get_queryset()

		if (user.is_superuser or user.role == User.Role.PROJECT_MANAGER):
			return base_qs

		# обычные пользователи должны видеть только свои задачи (created_by / assigned_to)
		return base_qs.filter(
			Q(created_by = user) | Q(assigned_to = user)
		)

	def perform_create(self, serializer: TaskSerializer):
		# внутри данные распаковываются в формате:
		# data = {**validated_data, **kwargs}
		# Одинаковые имена перезаписываются последним распакованным словарём.
		# Т.е kwargs перезаписывают данные validated_data

		serializer.save(created_by = self.request.user)


class CommentViewSet(ModelViewSet):
	serializer_class = CommentSerializer
	permission_classes = [
		IsAuthenticated & (
			# IsOptionsOrHead |
			# Это на десерт
		)
	]
	ordering = ['created_at'] # сначала старые, как на gh


	def get_queryset(self):
		task_pk = self.kwargs['task_pk']
		return Comment.objects.filter(task = task_pk)


	def perform_create(self, serializer: CommentSerializer):
		task_pk = self.kwargs['task_pk']
		serializer.save(
			created_by = self.request.user,
			task = Task.objects.get(pk = task_pk)
		)

