from django.db.models              import QuerySet 
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions    import IsAuthenticated
from rest_framework.viewsets       import ModelViewSet, GenericViewSet
from rest_framework.response       import Response
from rest_framework.filters        import SearchFilter, OrderingFilter
from rest_framework.request        import Request
from rest_framework                import mixins

from tasks.models import Task
from tasks.serializers import TaskSerializer
from tasks.permissions import IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff


class TaskViewSet(ModelViewSet):
	queryset = Task.objects.all().order_by('created_at')
	serializer_class = TaskSerializer
	permission_classes = [IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff]

	def perform_create(self, serializer: TaskSerializer):
		serializer.validated_data['created_by'] = self.request.user