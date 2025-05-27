from django.contrib.auth import get_user_model
from django.db           import models

User = get_user_model()


class Task(models.Model):
	class Priority(models.TextChoices):
		LOW    = ('low',    'Low')
		MEDIUM = ('medium', 'Medium')
		HIGH   = ('high',   'High')


	created_by   = models.ForeignKey(User, on_delete = models.CASCADE)
	title        = models.CharField (max_length = 255)
	priority     = models.CharField (max_length = 16, choices = Priority.choices)

	description  = models.TextField    (max_length = 8_192, null = True, blank = True)
	is_completed = models.BooleanField (default = False)
	created_at   = models.DateTimeField(auto_now_add = True)
	attachment   = models.FileField    (null = True, blank = True, upload_to = 'attachments/')
	due_date     = models.DateTimeField(null = True, blank = True)
	assigned_to  = models.ForeignKey   (User, on_delete = models.SET_NULL, null = True, blank = True)



class Comment(models.Model):
	task   = models.ForeignKey(Task, on_delete = models.CASCADE)
	author = models.ForeignKey(User, on_delete = models.CASCADE)
	content    = models.TextField(max_length = 2_048)
	created_at = models.DateTimeField(auto_now_add = True)
