from django.contrib.auth import get_user_model
from rest_framework      import serializers

from tasks.models import Task
from users.models import User as _User

User: type[_User] = get_user_model()


class TaskOwnerSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = (
			'id',
			'username',
			'email'
		)


class TaskSerializer(serializers.ModelSerializer):
	created_by = TaskOwnerSerializer(read_only = True)

	class Meta:
		model = Task
		fields = (
			'id',
			'title',
			'description',
			'is_completed',
			'created_by',
			'created_at',
			'attachment',
		)
		extra_kwargs = {
			'created_by': { 'read_only': True },
			'created_at': { 'read_only': True },
		}
