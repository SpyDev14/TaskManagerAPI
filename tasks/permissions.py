from django.contrib.auth        import get_user_model
from django.http.request        import HttpRequest
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from users.models import User
from tasks.models import Task

UserModel: type[User] = get_user_model()


class IsAuthenticatedAndIsReadOnlyOrOwnerOrProjectManagerOrStaff(IsAuthenticated):
	def has_object_permission(self, request: HttpRequest, view, obj: Task):

		return bool (
			super().has_object_permission(request, view, obj) and
			bool(
				request.method in SAFE_METHODS or
				obj.created_by == request.user or
				request.user.role == UserModel.Role.PROJECT_MANAGER or
				request.user.is_staff
			)
		)
