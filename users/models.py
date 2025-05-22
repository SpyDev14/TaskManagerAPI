from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as loc
from django.contrib.auth.hashers import make_password
from django.db import models


class User(AbstractUser):
	class Role(models.TextChoices):
		REGULAR_USER    = ('regular_user',    loc('Regular User'))
		PROJECT_MANAGER = ('project_manager', loc('Project Manager'))


	role = models.CharField(
		max_length = 32,
		choices = Role.choices,
		default = Role.REGULAR_USER,
		verbose_name = loc('Роль')
	)

	email = models.EmailField(blank = True, verbose_name = loc('Почта'))


	def __str__(self) -> str:
		return f'{self.username} ({self.get_role_display()})'