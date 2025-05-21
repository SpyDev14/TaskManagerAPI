from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
	class Role(models.TextChoices):
		REGULAR_USER    = ('regular_user',    'Regular User')
		PROJECT_MANAGER = ('project_manager', 'Project Manager')


	role = models.CharField(
		max_length = 32,
		choices = Role.choices,
		default = Role.REGULAR_USER
	)
	# сейчас это поле уже практически не нужно
	email = models.EmailField(unique = True, null = True, blank = True)


	def __str__(self) -> str:
		return self.username