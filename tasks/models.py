from django.utils import timezone
from django.conf import settings
from django.db import models


class Task(models.Model):
	created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE)
	title        = models.CharField(max_length = 255)
	description  = models.TextField(max_length = 16_367, null = True, blank = True)
	is_completed = models.BooleanField(default = False)
	created_at   = models.DateTimeField(default = timezone.now)
	attachment   = models.FileField(null = True, blank = True)


