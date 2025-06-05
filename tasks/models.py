from django.contrib.auth import get_user_model
from django.db           import models

from users.models import User as _User

User: type[_User] = get_user_model()

__all__ = [
	'Task',
	'Comment',
]

# в теории у задачи может быть владелец и другой назначенный человек
# если PM назначит
class Task(models.Model):
	class Priority(models.TextChoices):
		LOW    = ('low',    'Low')
		MEDIUM = ('medium', 'Medium')
		HIGH   = ('high',   'High')


	created_by = models.ForeignKey(
		User,
		on_delete = models.CASCADE,
		related_name = 'created_tasks',
		editable = False
	)
	title      = models.CharField (max_length = 255)
	priority   = models.CharField (max_length = 16, choices = Priority.choices)

	description  = models.TextField    (max_length = 8_192, null = True, blank = True)
	is_completed = models.BooleanField (default = False)
	created_at   = models.DateTimeField(auto_now_add = True, editable = False)
	attachment   = models.FileField    (null = True, blank = True, upload_to = 'attachments/')
	due_date     = models.DateTimeField(null = True, blank = True)
	assigned_to  = models.ForeignKey(
		User,
		on_delete = models.SET_NULL,
		related_name = 'assigned_tasks',
		null = True,
		blank = True
	)

	class Meta:
		# ordering = ['-id']
		get_latest_by = 'id'


	def __str__(self) -> str:
		return f'{self.title} - {self.created_by}'


class Comment(models.Model):
	task       = models.ForeignKey(Task, on_delete = models.CASCADE, related_name = 'comments', editable = False)
	created_by = models.ForeignKey(User, on_delete = models.CASCADE, related_name = 'comments', editable = False)

	content    = models.TextField(max_length = 2_048)
	created_at = models.DateTimeField(auto_now_add = True, editable = False)

	class Meta:
		ordering = ['-created_at']
