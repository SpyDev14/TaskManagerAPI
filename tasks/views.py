from django.db.models           import Q
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.viewsets    import ModelViewSet
from rest_framework             import generics

from tasks.permissions import IsOptionsOrHead, IsProjectManager, IsObjectOwner, IsAssignedToObject
from tasks.serializers import *
from tasks.models      import *


class TaskViewSet(ModelViewSet):
	# базовый QS, дополняется в get_qs()
	queryset = Task.objects.all().order_by('created_at')

	serializer_class = TaskSerializer
	permission_classes = [
		IsAuthenticated &
		(IsOptionsOrHead | IsObjectOwner | IsAssignedToObject | IsProjectManager | IsAdminUser)
	]

	def get_queryset(self):
		params: dict = {
			'request': self.request,
			'view': self
		}
		user = self.request.user
		base_qs = super().get_queryset()

		# if (IsAdminUser().has_permission(**params) or
		# 	IsProjectManager().has_permission(**params)):
		# 	return base_qs

		return base_qs.filter(
			Q(created_by = user) | Q(assigned_to = user)
		)

	def perform_create(self, serializer: TaskSerializer):
		serializer.validated_data['created_by'] = self.request.user
		serializer.save()
