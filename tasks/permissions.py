from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from django.http.request        import HttpRequest

from users.models import User
from tasks.models import Task


class IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff(IsAuthenticated):
	def has_object_permission(self, request: HttpRequest, view, obj: Task):
		return bool (
			super().has_object_permission(request, view, obj) and
			bool(
				request.method in SAFE_METHODS or
				obj.created_by == request.user or
				request.user.role == User.Role.PROJECT_MANAGER or
				request.user.is_staff
			)
		)