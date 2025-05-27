from django.conf import settings
from django.db   import models


class Task(models.Model):
	created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE)
	title        = models.CharField(max_length = 255)
	description  = models.TextField(max_length = 8_190, null = True, blank = True)
	is_completed = models.BooleanField(default = False)
	created_at   = models.DateTimeField(auto_now_add = True)
	attachment   = models.FileField(null = True, blank = True, upload_to = 'attachments/')
