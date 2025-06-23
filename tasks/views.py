from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth           import get_user_model
from django.db.models              import Prefetch
from rest_framework.viewsets       import ModelViewSet, GenericViewSet
from rest_framework.filters        import SearchFilter
from rest_framework                import mixins

from users.models      import User as _User
from tasks.serializers import FIELDS_FOR_USER_INFO_SERIALIZER
from tasks.serializers import *
from tasks.permissions import *
from tasks.filters     import TaskOrderingFilter, OrderingFilter
from tasks.models      import *

User: type[_User] = get_user_model()

# Нужен ли list? Пока оставлю, потом можно будет убрать.
class CommentViewSet(
		mixins.CreateModelMixin,
		mixins.UpdateModelMixin,
		mixins.DestroyModelMixin,
		mixins.ListModelMixin,
		GenericViewSet,
	):
	serializer_class = CommentSerializer
	permission_classes = [CommentsUnderTaskPermission]
	filter_backends  = [OrderingFilter]
	ordering_fields = ['created_at']
	ordering = ['created_at']


	def get_queryset(self):
		task_pk = self.kwargs['task_pk']
		return (
			Comment.objects
				.filter(task = task_pk)
				.select_related('created_by')
		)

	def perform_create(self, serializer: CommentSerializer):
		task_pk = self.kwargs['task_pk']
		serializer.save(
			created_by = self.request.user,
			task = Task.objects.get(pk = task_pk)
		)

class TaskViewSet(ModelViewSet):
	serializer_class = TaskSerializer
	permission_classes = [(
		IsOptionsOrHead | (
			IsAuthenticated & (
				IsAdminUser   | IsProjectManager |
				IsObjectOwner | (IsAssignedToObject & IsNotDeleteMethod)
			)
		)
	)]
	filter_backends  = [TaskOrderingFilter, DjangoFilterBackend, SearchFilter]
	filterset_fields = ['priority', 'assigned_to', 'is_completed']
	search_fields    = ['title', 'description']
	ordering_fields  = ['due_date', 'created_at']
	ordering = ['created_at']

	COMMENTS_IN_DETAIL_ORDERING: list[str] = CommentViewSet.ordering


	# Вызывает ошибку 404 вместо 403 при обращении к чужой задаче. С точки зрения 
	# безопасности, так даже лучше.
	def get_queryset(self):
		q_filter = get_task_qs_filter_with_permissions(self)
		qs = (
			Task.objects
				.select_related('created_by', 'assigned_to')
				.filter(q_filter)
		)


		self.kwargs: dict
		if self.kwargs.get('pk', False):
			task_pk = self.kwargs['pk']
			prefetch_comments = Prefetch(
				'comments',
				Comment.objects
					.filter(task = task_pk)
					.order_by(*self.COMMENTS_IN_DETAIL_ORDERING)
					.select_related('created_by')
			)

			qs = qs.prefetch_related(prefetch_comments)


		return qs

	def perform_create(self, serializer: TaskSerializer):
		serializer.save(created_by = self.request.user)
