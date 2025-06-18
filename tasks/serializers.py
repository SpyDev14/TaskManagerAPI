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

FIELDS_FOR_USER_INFO_SERIALIZER: tuple[str] = UserInfoSerializer.Meta.fields

class CommentSerializer(serializers.ModelSerializer):
	created_by = UserInfoSerializer(read_only = True)

	class Meta:
		model = Comment
		exclude = ['task']


def _user_has_not_permission_to_edit_assigned_to(user: _User) -> bool:
	return user.role == User.Role.REGULAR_USER and not user.is_superuser

class TaskSerializer(serializers.ModelSerializer):
	created_by  = UserInfoSerializer(read_only = True)
	assigned_to = UserInfoSerializer(read_only = True)
	# Либо через переопределение to_representation с подменой. ИИ сказал, вот это по RESTу
	assigned_to_id = serializers.PrimaryKeyRelatedField(
		source = 'assigned_to',
		queryset = User.objects.all(),
		write_only = True,
		required = False,
		allow_null = True
	)

	# Динамически удаляется при many
	comments = CommentSerializer(many = True, read_only = True)

	class Meta:
		model = Task
		fields = '__all__'
		exclude_on_many_fields = ['attachment', 'comments']


	def get_fields(self):
		fields = super().get_fields()
		if isinstance(self.parent, serializers.ListSerializer):
			for field in self.Meta.exclude_on_many_fields:
				fields.pop(field)
		return fields

	# обычные пользователи не могут редактировать или задавать при создании assigned_to
	def validate(self, attrs: dict):
		# если сериализатор вызывается из view (т.е API) - там точно будет request
		# иначе он вызывается где-то в коде (скорее всего в тестах) и там не нужна
		# эта обработка.
		if 'request' not in self.context:
			return attrs
		
		user: _User = self.context['request'].user

		if _user_has_not_permission_to_edit_assigned_to(user):
			attrs.pop('assigned_to', None)

		return attrs


	# При создании задачи, если пользователь из запроса это regular user - он
	# автоматически устанавливается в поле assigned_to.
	# Если это ПМ или суперадмин - поле assigned_to обрабатывается по умолчанию.
	def create(self, validated_data):
		user: _User = validated_data['created_by']

		# обычные пользователи назначаются на свою задачу
		if _user_has_not_permission_to_edit_assigned_to(user):
			validated_data['assigned_to'] = user

		task: Task = super().create(validated_data)
		assert (task.created_by == task.assigned_to) or (
			task.created_by.role != User.Role.REGULAR_USER or
			user.is_superuser
		)

		return task
