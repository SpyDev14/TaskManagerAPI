from rest_framework.viewsets       import ModelViewSet

from tasks.models import Task
from tasks.serializers import TaskSerializer
from tasks.permissions import IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff


class TaskViewSet(ModelViewSet):
	queryset = Task.objects.all().order_by('created_at')
	serializer_class = TaskSerializer
	permission_classes = [IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff]

	def perform_create(self, serializer: TaskSerializer):
		serializer.validated_data['created_by'] = self.request.user
		serializer.save()