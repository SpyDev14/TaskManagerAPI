from django.contrib.auth        import get_user_model
from django.db.models           import Q, QuerySet
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.viewsets    import ModelViewSet
from rest_framework             import generics

from users.models      import User as _User
from tasks.permissions import *
from tasks.serializers import *
from tasks.models      import *

User: type[_User] = get_user_model()


class TaskViewSet(ModelViewSet):
	# базовый QS, дополняется в get_qs()
	queryset = Task.objects.all()

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

	# небольшое нарушение solid, так как за права ролей отвечает метод получения qs
	def get_queryset(self):
		user: _User = self.request.user
		base_qs = super().get_queryset()

		if (user.is_superuser or user.role == User.Role.PROJECT_MANAGER):
			return base_qs

		# обычные пользователи видят только свои задачи
		return base_qs.filter(
			Q(created_by = user) | Q(assigned_to = user)
		)

	def perform_create(self, serializer: TaskSerializer):
		serializer.validated_data['created_by'] = self.request.user
		serializer.save()
