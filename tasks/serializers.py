from django.contrib.auth import get_user_model
from rest_framework      import serializers

from tasks.models import Task, Comment
from users.models import User as _User

User: type[_User] = get_user_model()

__all__ = [
	'TaskSerializer',
	'CommentSerializer',
]

class UserInfoSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = (
			'id',
			'username',
			'email',
			'first_name',
			'last_name',
		)


class CommentSerializer(serializers.ModelSerializer):
	created_by = UserInfoSerializer(read_only = True)

	class Meta:
		model = Comment
		exclude = ['task']


class TaskSerializer(serializers.ModelSerializer):
	created_by  = UserInfoSerializer(read_only = True)
	assigned_to = UserInfoSerializer(read_only = True)
	# Либо через переопределение to_representation с подменой, ИИ сказал вот это по REST vvv
	assigned_to_id = serializers.PrimaryKeyRelatedField(
		source = 'assigned_to',
		queryset = User.objects.all(),
		write_only = True
	)

	# Динамически удаляется при many
	comments = CommentSerializer(many = True, read_only = True)

	class Meta:
		model = Task
		fields = '__all__'
		# extra_kwargs = {
		# 	'assigned_to': {'write_only': False}
		# }
	
	def get_fields(self):
		fields = super().get_fields()
		if isinstance(self.parent, serializers.ListSerializer):
			fields.pop('comments')
		return fields


	# При создании задачи, если пользователь из запроса это regular user - он
	# автоматически устанавливается в поле assigned_to.
	# Если это ПМ или суперадмин - поле assigned_to обрабатывается по умолчанию.
	def create(self, validated_data):
		user: _User = validated_data['created_by']

		# обычные пользователи сами назначаются на свою задачу
		if user.role == User.Role.REGULAR_USER and not user.is_superuser:
			validated_data['assigned_to'] = user

		task: Task = super().create(validated_data)
		assert (task.created_by == task.assigned_to) or (
			task.created_by.role != User.Role.REGULAR_USER or
			user.is_superuser
		)

		return task
