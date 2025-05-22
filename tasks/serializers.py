from rest_framework import serializers

from tasks.models import Task
from users.models import User



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