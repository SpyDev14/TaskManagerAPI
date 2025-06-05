from django.contrib.auth import get_user_model
from rest_framework      import serializers

from tasks.models import Task, Comment
from users.models import User as _User

User: type[_User] = get_user_model()

__all__ = [
	'TaskSerializer',
	'CommentSerializer',
	'CommentForTaskSerializer',
]

class UserInfoSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = (
			'id',
			'username',
			'email'
		)


class CommentSerializer(serializers.ModelSerializer):
	created_by = UserInfoSerializer(read_only = True)

	class Meta:
		model = Comment
		fields = (
			'id',
			'task',
			'created_by',
			'created_at',
			'content',
		)
		extra_kwargs = {
			'task': { 'read_only': True }
		}


class CommentForTaskSerializer(CommentSerializer):
	class Meta(CommentSerializer.Meta):
		fields = (
			'id',
			'task',
			'created_by',
			'created_at',
			'content',
		)


class TaskSerializer(serializers.ModelSerializer):
	created_by  = UserInfoSerializer(read_only = True)
	assigned_to = UserInfoSerializer(read_only = True)
	# прописано в Comment.task related_name (т.е можно обратится через Task.comments)
	# нужно удалять поле из self.fields, если many = True
	comments    = CommentForTaskSerializer(many = True, read_only = True)

	class Meta:
		model = Task
		fields = '__all__'


	# при создании, если создатель - это regular user,
	# мы должны установить его в assigned_to. А если это
	# PM - то мы не должны ничего делать, пускай творит
	# с этим полем всё что хочет.
	def create(self, validated_data):
		user: _User = validated_data['created_by']

		# также это гарантирует, что простой пользователь
		# не может назначить кого-то на свою задачу
		if user.role == User.Role.REGULAR_USER:
			validated_data['assigned_to'] = user

		task: Task = super().create(validated_data)
		assert (task.created_by == task.assigned_to) or task.created_by.role != User.Role.REGULAR_USER

		return task
